# Missing Features - Status Update

## ✅ Completed Items

### 1. Real change callbacks
**Status: FIXED**
- Implemented `on_change` decorator in Config class
- Added `_trigger_change_callbacks` method that fires when configuration reloads
- Callbacks receive (key, old_value, new_value) on changes
- Integrated with IDE stub regeneration

### 2. CLI parity for validation/export/debug
**Status: FIXED**
- Added `config-stash validate` command with schema support
- Added `config-stash export` command supporting json/yaml/toml formats
- Added `config-stash debug` command with key-specific and report export options
- All commands are now available and functional

### 3. .env / INI loaders and env separator
**Status: FIXED**
- Created `EnvFileLoader` for .env file support with dot notation for nesting
- Created `IniLoader` for INI configuration files
- Updated `EnvironmentLoader` to accept custom separator parameter (default: "__")
- Added type casting support in all loaders

### 4. Deep merge for nested overrides
**Status: FIXED**
- Added `deep_merge` parameter to Config.__init__ (default: True)
- Config now calls ConfigMerger.merge_configs with deep_merge flag
- Properly handles nested configuration merges instead of replacing whole subtrees

## ⚠️ Pending Items

### Secret-store integration
**Status: DEFERRED**
- VaultResolver remains a placeholder with NotImplementedError
- This is intentionally deferred to a future release
- Current recommendation: Use environment variables for sensitive data
- Not advertised as a current feature in README

## Summary
All critical missing features have been implemented except for secret store integration, which is appropriately marked as a future enhancement and not advertised as a current capability.