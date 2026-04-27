# Axessia — Accessibility Intelligence Platform

## Quick Deploy to Azure

```bash
git init
git remote add origin https://github.com/sky-vino/Axessia-.git
git branch -M main
git add .
git commit -m "Deploy Axessia"
git push origin main --force
```

## Verify deployment
After pushing, wait 5 minutes then test:
- Health check: https://axessia-app-b6b4gtbxhzfpa3bn.francecentral-01.azurewebsites.net/health
- App: https://axessia-app-b6b4gtbxhzfpa3bn.francecentral-01.azurewebsites.net

## Required Azure App Service settings
Go to: App Service → Configuration → Application settings

Required environment variables:
- AZURE_OPENAI_ENDPOINT
- AZURE_OPENAI_KEY
- AZURE_OPENAI_API_VERSION=2024-02-01
- AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
- AXESSIA_API_KEY (any strong random string)
- AXESSIA_API_URL=http://127.0.0.1:8001/scan
- WEBSITES_PORT=8000
- SCM_DO_BUILD_DURING_DEPLOYMENT=false
- PLAYWRIGHT_BROWSERS_PATH=/home/playwright-browsers

Startup command (App Service → Configuration → General settings):
```
bash startup.sh
```

Stack: Python 3.10
