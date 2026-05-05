module.exports = {
  apps: [{
    name: 'policy-engine',
    script: 'main.py',
    cwd: '/tmp/policypilot/engine',
    interpreter: 'python3',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '500M',
    env: {
      PYTHONUNBUFFERED: '1'
    }
  }]
};
