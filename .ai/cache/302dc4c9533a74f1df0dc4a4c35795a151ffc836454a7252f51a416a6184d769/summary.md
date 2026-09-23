# File Contract Summary: `web/static/app_backup.js`
- **Lines**: 1566
- **Symbols Count**: 64
- **Imports Count**: 0

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `function` | **`formatBytes`** | `global` | L23-L23 | args: (bytes) |
| `function` | **`formatDate`** | `global` | L31-L31 | args: (isoStr) |
| `function` | **`switchTab`** | `global` | L41-L41 | args: (tabId) |
| `function` | **`fetchAPI`** | `global` | L65-L65 | args: (url, options = {}) |
| `function` | **`loadDashboard`** | `global` | L83-L83 |  |
| `function` | **`renderDashboardStats`** | `global` | L105-L105 |  |
| `function` | **`renderSystemDrives`** | `global` | L117-L117 |  |
| `function` | **`renderRecentSnapshots`** | `global` | L138-L138 |  |
| `function` | **`loadSnapshots`** | `global` | L190-L190 |  |
| `function` | **`renderSnapshotsTable`** | `global` | L199-L199 |  |
| `function` | **`inspectSnapshot`** | `global` | L260-L260 | args: (snapshotId) |
| `function` | **`loadExplorerPath`** | `global` | L288-L288 | args: (subpath) |
| `function` | **`renderExplorerBreadcrumb`** | `global` | L311-L311 | args: (subpath) |
| `function` | **`filterExplorerItems`** | `global` | L340-L340 |  |
| `function` | **`renderExplorerItems`** | `global` | L346-L346 |  |
| `function` | **`verifySnapshot`** | `global` | L412-L412 | args: (snapshotId) |
| `function` | **`deleteSnapshot`** | `global` | L429-L429 | args: (snapshotId) |
| `function` | **`openRestoreModal`** | `global` | L441-L441 | args: (snapshotId, targetRelPath = null, targetName = null, targetType = null) |
| `function` | **`clearSelectiveRestore`** | `global` | L486-L486 |  |
| `function` | **`toggleRestoreMode`** | `global` | L493-L493 |  |
| `function` | **`startRestore`** | `global` | L521-L521 |  |
| `function` | **`triggerQuickBackup`** | `global` | L562-L562 |  |
| `function` | **`cancelCurrentTask`** | `global` | L578-L578 |  |
| `function` | **`pollTaskStatus`** | `global` | L588-L588 |  |
| `function` | **`loadProfiles`** | `global` | L656-L656 |  |
| `function` | **`renderProfilesList`** | `global` | L666-L666 |  |
| `function` | **`onScheduleTypeChange`** | `global` | L741-L741 |  |
| `function` | **`openCreateProfileModal`** | `global` | L758-L758 |  |
| `function` | **`editProfile`** | `global` | L775-L775 | args: (profileId) |
| `function` | **`saveProfileFromModal`** | `global` | L800-L800 |  |
| `function` | **`triggerProfileBackup`** | `global` | L848-L848 | args: (profileId) |
| `function` | **`deleteProfile`** | `global` | L860-L860 | args: (profileId, profileName) |
| `function` | **`loadWindowsTaskStatus`** | `global` | L873-L873 |  |
| `function` | **`registerWindowsTaskFromUI`** | `global` | L894-L894 |  |
| `function` | **`unregisterWindowsTaskFromUI`** | `global` | L921-L921 |  |
| `function` | **`runGarbageCollection`** | `global` | L933-L933 |  |
| `function` | **`openDirectoryPicker`** | `global` | L945-L945 | args: (targetInputId) |
| `function` | **`browseToDirectory`** | `global` | L960-L960 | args: (path) |
| `function` | **`selectBrowsePath`** | `global` | L1000-L1000 | args: (path) |
| `function` | **`selectCurrentBrowsePath`** | `global` | L1007-L1007 |  |
| `function` | **`loadCustomSelectionData`** | `global` | L1015-L1015 |  |
| `function` | **`renderInstalledApps`** | `global` | L1044-L1044 | args: (filterText = '') |
| `function` | **`filterAppsList`** | `global` | L1090-L1090 |  |
| `function` | **`saveCustomSelectionState`** | `global` | L1096-L1096 |  |
| `function` | **`restoreCustomSelectionState`** | `global` | L1112-L1112 |  |
| `function` | **`toggleAppSelectionByIndex`** | `global` | L1160-L1160 | args: (idx) |
| `function` | **`toggleAllApps`** | `global` | L1175-L1175 | args: (select) |
| `function` | **`renderAiProjects`** | `global` | L1188-L1188 |  |
| `function` | **`toggleProjectSelectionByIndex`** | `global` | L1213-L1213 | args: (idx) |
| `function` | **`toggleAllProjects`** | `global` | L1227-L1227 | args: (select) |
| `function` | **`openDirectoryPickerForCustom`** | `global` | L1238-L1238 |  |
| `function` | **`removeCustomFolder`** | `global` | L1251-L1251 | args: (idx) |
| `function` | **`renderCustomFoldersList`** | `global` | L1258-L1258 |  |
| `function` | **`updateCustomSummary`** | `global` | L1282-L1282 |  |
| `function` | **`startCustomSelectionBackup`** | `global` | L1308-L1308 |  |
| `function` | **`loadSystemImageStatus`** | `global` | L1346-L1346 |  |
| `function` | **`updateSystemImageRunningUI`** | `global` | L1400-L1400 | args: (isRunning) |
| `function` | **`startSystemImageBackup`** | `global` | L1431-L1431 |  |
| `function` | **`startPollingSystemImageLogs`** | `global` | L1467-L1467 |  |
| `function` | **`stopSystemImageBackup`** | `global` | L1499-L1499 |  |
| `function` | **`verifySnapshot`** | `global` | L1509-L1509 | args: (snapshotId) |
| `function` | **`openModal`** | `global` | L1528-L1528 | args: (id) |
| `function` | **`closeModal`** | `global` | L1533-L1533 | args: (id) |
| `function` | **`shutdownServer`** | `global` | L1538-L1538 |  |

