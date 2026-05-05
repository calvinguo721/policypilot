module.exports = {
  apps: [{
    name: 'policypilot',
    script: '/usr/bin/python3',
    args: '-m uvicorn engine.main:app --host 0.0.0.0 --port 8002',
    cwd: '/tmp/policypilot',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '500M',
    env: {
      PYTHONUNBUFFERED: '1'
    }
  }]
};
