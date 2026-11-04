'use strict';
// Direct MT5 onboarding API: demo-only, encrypted, read-only validation.
// No routes in this file can place or modify broker orders.
const crypto = require('node:crypto');
const { encryptCredential, decryptCredential } = require('./credentialCrypto');
const { validateDemoAccount, validUuid, validWorkerId } = require('./demoAccountValidation');

async function initDemoDB(pool) {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS demo_mt5_accounts (
      id UUID PRIMARY KEY,
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      login VARCHAR(20) NOT NULL,
      server VARCHAR(128) NOT NULL,
      label VARCHAR(80) NOT NULL DEFAULT '',
      password_enc TEXT,
      status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','verified_demo','rejected_live','failed')),
      last_error_code VARCHAR(40),
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      UNIQUE (user_id,login,server)
    )
  `);
  await pool.query(`
    CREATE TABLE IF NOT EXISTS demo_mt5_jobs (
      id UUID PRIMARY KEY,
      account_id UUID NOT NULL UNIQUE REFERENCES demo_mt5_accounts(id) ON DELETE CASCADE,
      state VARCHAR(20) NOT NULL DEFAULT 'queued'
        CHECK (state IN ('queued','running','completed','failed')),
      worker_id VARCHAR(64),
      lease_until TIMESTAMPTZ,
      attempts INTEGER NOT NULL DEFAULT 0,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      completed_at TIMESTAMPTZ
    )
  `);
  await pool.query(`CREATE INDEX IF NOT EXISTS demo_mt5_jobs_claim_idx
    ON demo_mt5_jobs (state,created_at)`);
}

function workerAuthenticated(req) {
  const configured = process.env.MYFLOWFX_WORKER_TOKEN;
  const raw = req.headers.authorization;
  if (!configured || configured.length < 32 || !raw || !raw.startsWith('Bearer '))
    return false;
  const actual = Buffer.from(raw.slice(7), 'utf8');
  const expected = Buffer.from(configured, 'utf8');
  return actual.length === expected.length && crypto.timingSafeEqual(actual,expected);
}

function registerDemoAccountsApi(app, pool, authMiddleware) {
  const rejectWorker = (req,res,next) => {
    res.set('Cache-Control','no-store');
    if (!workerAuthenticated(req)) return res.status(401).json({error:'Non autorisé'});
    next();
  };
  const noStore = (_req,res,next) => {res.set('Cache-Control','no-store');next();};

  app.get('/api/demo/accounts',authMiddleware,noStore,async(req,res)=>{
    try {
      const r=await pool.query(
        `SELECT id,login,server,label,status,last_error_code,created_at,updated_at
          FROM demo_mt5_accounts WHERE user_id=$1 ORDER BY created_at DESC`,[req.user.id]);
      res.json({accounts:r.rows,executionEnabled:false});
    } catch(_e) {
      res.status(500).json({error:'Impossible de charger les comptes'});
    }
  });

  app.post('/api/demo/accounts',authMiddleware,noStore,async(req,res)=>{
    const validation=validateDemoAccount(req.body);
    if(validation.error) return res.status(400).json({error:validation.error});
    if(!process.env.MYFLOWFX_CREDENTIAL_KEY) {
      return res.status(503).json({error:'Connexion MT5 non configurée côté serveur'});
    }
    const client=await pool.connect();
    try {
      const {login,server,password,label}=validation.account;
      const accountId=crypto.randomUUID();
      const jobId=crypto.randomUUID();
      const encrypted=encryptCredential(password,req.user.id,accountId);
      await client.query('BEGIN');
      // Limit the number of onboarding accounts during the demo beta.
      const count=await client.query(
        'SELECT COUNT(*)::integer AS total FROM demo_mt5_accounts WHERE user_id=$1',[req.user.id]);
      if(count.rows[0].total>=5) {
        await client.query('ROLLBACK');
        return res.status(409).json({error:'Limite de 5 comptes démo atteinte'});
      }
      await client.query(
        `INSERT INTO demo_mt5_accounts(id,user_id,login,server,label,password_enc)
          VALUES($1,$2,$3,$4,$5,$6)`,
        [accountId,req.user.id,login,server,label,encrypted]);
      await client.query(
        'INSERT INTO demo_mt5_jobs(id,account_id) VALUES($1,$2)',[jobId,accountId]);
      await client.query('COMMIT');
      res.status(201).json({id:accountId,status:'pending',message:'Compte enregistré. Vérification démo en attente du serveur Windows.'});
    } catch(e) {
      await client.query('ROLLBACK').catch(()=>{});
      if(e.code==='23505') return res.status(409).json({error:'Ce compte MT5 existe déjà'});
      res.status(500).json({error:'Impossible d’enregistrer le compte'});
    } finally {
      client.release();
    }
  });

  app.delete('/api/demo/accounts/:id',authMiddleware,noStore,async(req,res)=>{
    if(!validUuid(req.params.id)) return res.status(400).json({error:'Identifiant invalide'});
    try {
      const r=await pool.query(
        'DELETE FROM demo_mt5_accounts WHERE id=$1 AND user_id=$2 RETURNING id',
        [req.params.id,req.user.id]);
      if(!r.rowCount) return res.status(404).json({error:'Compte introuvable'});
      res.json({deleted:true});
    } catch(_e) {
      res.status(500).json({error:'Impossible de supprimer le compte'});
    }
  });

  // Worker receives credentials ONLY on a mutually expected TLS connection,
  // and ONLY for a read-only demo validation job.
  app.post('/api/demo/worker/claim',rejectWorker,async(req,res)=>{
    const workerId=req.headers['x-worker-id'];
    if(!validWorkerId(workerId)) return res.status(400).json({error:'Worker invalide'});
    if(!process.env.MYFLOWFX_CREDENTIAL_KEY) {
      return res.status(503).json({error:'Service non configuré'});
    }
    const client=await pool.connect();
    try {
      await client.query('BEGIN');
      const next=await client.query(`
        SELECT j.id AS job_id,j.account_id,a.user_id,a.login,a.server,a.password_enc
        FROM demo_mt5_jobs j JOIN demo_mt5_accounts a ON a.id=j.account_id
        WHERE a.status='pending'
          AND ((j.state='queued' AND j.attempts<3)
            OR (j.state='running' AND j.lease_until<NOW() AND j.attempts<3))
        ORDER BY j.created_at
        FOR UPDATE OF j SKIP LOCKED LIMIT 1
      `);
      if(!next.rowCount) {
        await client.query('COMMIT');
        return res.status(204).end();
      }
      const item=next.rows[0];
      const password=decryptCredential(item.password_enc,item.user_id,item.account_id);
      await client.query(`
        UPDATE demo_mt5_jobs
        SET state='running',worker_id=$2,lease_until=NOW()+INTERVAL '120 seconds',
            attempts=attempts+1
        WHERE id=$1`,[item.job_id,workerId]);
      await client.query('COMMIT');
      res.json({
        jobId:item.job_id,
        accountId:item.account_id,
        login:item.login,
        server:item.server,
        password,
        mode:'read_only_demo_verification'
      });
    } catch(_e) {
      await client.query('ROLLBACK').catch(()=>{});
      res.status(503).json({error:'Vérification indisponible'});
    } finally {
      client.release();
    }
  });

  app.post('/api/demo/worker/result',rejectWorker,async(req,res)=>{
    const workerId=req.headers['x-worker-id'];
    const {jobId,result,accountLogin,errorCode}=req.body||{};
    if(!validWorkerId(workerId)||!validUuid(jobId)||
       !['verified_demo','rejected_live','failed'].includes(result)||
       (accountLogin!==undefined && (typeof accountLogin!=='string'||!/^[0-9]{1,20}$/.test(accountLogin)))) {
      return res.status(400).json({error:'Résultat invalide'});
    }
    const safeCode=['INVALID_CREDENTIALS','TERMINAL_UNAVAILABLE','ACCOUNT_MISMATCH','NETWORK_ERROR','UNKNOWN'].includes(errorCode)
      ? errorCode : 'UNKNOWN';
    const client=await pool.connect();
    try {
      await client.query('BEGIN');
      const r=await client.query(`
        SELECT j.account_id,a.login FROM demo_mt5_jobs j
        JOIN demo_mt5_accounts a ON a.id=j.account_id
        WHERE j.id=$1 AND j.state='running' AND j.worker_id=$2
          AND j.lease_until>NOW()
        FOR UPDATE OF j,a`,[jobId,workerId]);
      if(!r.rowCount) {
        await client.query('ROLLBACK');
        return res.status(409).json({error:'Travail expiré ou non attribué'});
      }
      if(result==='verified_demo' && accountLogin!==r.rows[0].login) {
        await client.query('ROLLBACK');
        return res.status(400).json({error:'Identifiant du compte différent'});
      }
      const status=result;
      const error=status==='verified_demo'?null:
        status==='rejected_live'?'DEMO_ONLY':safeCode;
      // Discard credentials immediately for any identified live account.
      await client.query(`
        UPDATE demo_mt5_accounts
        SET status=$2,last_error_code=$3,updated_at=NOW(),
            password_enc=CASE WHEN $2='rejected_live' THEN NULL ELSE password_enc END
        WHERE id=$1`,[r.rows[0].account_id,status,error]);
      await client.query(`
        UPDATE demo_mt5_jobs
        SET state=$2,completed_at=NOW(),lease_until=NULL
        WHERE id=$1`,[jobId,status==='failed'?'failed':'completed']);
      await client.query('COMMIT');
      res.json({ok:true});
    } catch(_e) {
      await client.query('ROLLBACK').catch(()=>{});
      res.status(500).json({error:'Impossible de valider le résultat'});
    } finally {
      client.release();
    }
  });

  app.get('/api/demo/engine/status',authMiddleware,noStore,(_req,res)=>{
    res.json({status:'verification_only',autoTradingEnabled:false,
      note:'Seuls les comptes DEMO sont acceptés. Aucun ordre n’est exécuté.'});
  });
}
module.exports={initDemoDB,registerDemoAccountsApi};
