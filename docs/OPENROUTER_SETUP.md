# OpenRouter API Key Setup Guide

This guide will help you set up and manage your OpenRouter API key for DocVaultAI.

## Quick Start

1. **Get your API key:**
   - Visit: https://openrouter.ai/keys
   - Sign up or log in
   - Create a new API key

2. **Add to `.env` file:**
   ```bash
   OPENROUTER_API_KEY=sk-or-v1-your-key-here
   AI_PROVIDER=openrouter
   ```

3. **Test your key:**
   ```bash
   cd backend
   python3 scripts/test_openrouter.py
   ```

## Current Status

### ✅ Configuration
- **AI Provider:** `openrouter`
- **Base URL:** `https://openrouter.ai/api/v1`
- **API Key:** Set in `.env` file

### ⚠️ Current Issue
Your API key is **valid** but your account has **insufficient credits**.

## Adding Credits

1. Visit: https://openrouter.ai/settings/credits
2. Add credits to your account
3. The system will automatically start using real AI instead of fallback

## Testing Your API Key

### Method 1: Using the test script
```bash
cd backend
python3 scripts/test_openrouter.py
```

### Method 2: Test a specific key
```bash
python3 scripts/test_openrouter.py --key sk-or-v1-your-key-here
```

### Method 3: Check configuration only
```bash
python3 scripts/test_openrouter.py --check
```

## Updating Your API Key

1. **Get a new key from OpenRouter:**
   - Visit: https://openrouter.ai/keys
   - Create a new API key

2. **Update `.env` file:**
   ```bash
   OPENROUTER_API_KEY=sk-or-v1-your-new-key-here
   ```

3. **Restart the backend:**
   ```bash
   # The backend will automatically reload with the new key
   ```

## Troubleshooting

### Error: "Insufficient credits" (402)
- **Solution:** Add credits at https://openrouter.ai/settings/credits
- The system will use MockProvider fallback until credits are added

### Error: "Unauthorized" (401)
- **Solution:** Your API key is invalid
- Get a new key from https://openrouter.ai/keys
- Update `.env` file with the new key

### Error: "API key not configured"
- **Solution:** Make sure `.env` file exists in the `backend/` directory
- Add `OPENROUTER_API_KEY=your-key-here` to the file

## Models Used

DocVaultAI uses the following models via OpenRouter:

- **Chat Completions:** `anthropic/claude-3-haiku`
- **Embeddings:** `text-embedding-ada-002` (with fallback to `text-embedding-3-small`)

## Cost Estimation

OpenRouter pricing varies by model. Check current pricing at:
https://openrouter.ai/models

Typical costs:
- Claude 3 Haiku: ~$0.25 per 1M input tokens
- Text Embedding Ada 002: ~$0.10 per 1M tokens

## Fallback Behavior

If OpenRouter API calls fail (due to credits or errors), the system automatically falls back to:
- **MockProvider:** Provides basic functionality for testing
- **Text-based search:** Works without embeddings

This ensures the application continues working even without API credits.

## Support

- OpenRouter Docs: https://openrouter.ai/docs
- OpenRouter Discord: https://discord.gg/openrouter
- OpenRouter Status: https://status.openrouter.ai

