# <img src="icons/juneai.png" width="40" /> JuneAI Soft

---

## [v2.1.5] - 10th January 2026
- Soft has been translated into English
- GPU, UserAgent, and screen resolution rotation modules removed due to redundancy
- Soft updated for general release
- README.md has been updated

## [v2.1.4] - 19th December 2025
- Fixed various bugs

## [v2.1.3] - 12th December 2025
- Software adapted for the new UI update

## [v2.1.2] - 12th November 2025
- Added file with prompts for video (**prompts/videos.txt**)
- Added video farming
- Added check for unavailable cursor when clicking on input field; script skips current model and continues
- Added User-Agent rotation (50)
- Added screen resolution rotation
- Improved `startDelay` parameter for synchronized profiles

## [v2.1.1] - 31th October 2025
- Changed profile launch logic: second account won't start if first is still loading
- Adjusted script for June site UI updates
- Fixed resolution to stabilize farming
- Added new models for farming
- Added profile numbering in the menu table

## [v2.0.1] - 19th October 2025
- Added new config parameters: *hidden*, *startDelay*, *retries*
- Removed `autoCloseBrowser` from config; software now closes profiles automatically
- Improved image model click logic
- Fixed auto-login logic for logged-out accounts
- Adjusted agent response wait to prevent bans

## [v2] - 7th October 2025
- Optimized farming speed
- Removed fixed screen resolution for browsers
- Added IMAP integration (see README)
- Profiles display current points on launch
- Profiles with "!" appear at bottom, others on top
- Added `threadCount` config
- Removed last two models in queue for speed
- Optimized and improved code structure
- Added check for cookie folders; flagged profiles with "!"
- Adjusted profile launch delay to 3-9 seconds
- Renamed software

## [v1.9] - 3rd October 2025
- Config moved to root
- Adjusted timings
- Prompt language changed to English
- Text prompts increased: 1k → 1.5k
- Image prompts increased: 1k → 2k
- Points fetched directly from server, not page elements
- Points display updated: +<points per request>
- Boolean values standardized: "true" → true, "y" → true
- "Starting..." message added on launch
- Last three models removed for faster farming

## [v1.8 Fix] - 1st October 2025
- Fixed auto-close bug
- Added Python 3.13 launch parameter

## [v1.8] - 30th September 2025
- Fixed bug with unlogged profiles not marked
- Updated log and warning theme (colors configurable in config)
- Updated Claude Sonnet model version 4 → 4.5
- Added auto-close profile option
- Renamed terminal window title to "June Soft v1.8"
- Adjusted timings
- README updated

## [v1.7] - 28th September 2025
- Improved code structure
- Added `pycache` folder for centralized caching
- Profiles now launch with delay to avoid blocks

## [v1.6 Beta] - 26th September 2025
- Libraries loaded locally: added `chromium` and `libs` folders
- Adjusted timings
- Added new image model
- Added performance checks
- Reorganized source folder
- User-Agent data updated for anti-bot protection

## [v1.5] - 21th September 2025
- Fixed double farming loop bug
- Added 24-hour continuous farming with 5-hour breaks for points refresh
- Profiles auto-close after farming

## [v1.4] - 20th September 2025
- Added proxy support; edit `profiles.json`
- Profiles with "!" do not launch during full farm
- Menu updated
- Unique prompts increased: text 409→1001, image 409→1001
- Minor bug fixes
- Improved file structure

## [v1.3] - 17th September 2025
- Fixed real-time points reading
- Fixed random infinite page load (reloads after 3s)
- Faster menu loading after browser closes

## [v1.2] - 16th September 2025
- Requests only after points top-up; skips models if points not updated
- Menu color customization via `config.json` HEX codes
- Optimized click timings
- Farming algorithm improved (clarity, optimization, functionality)
- Profiles can now launch in parallel safely

## [v1.2 beta] - 15th September 2025
- Added image farming system
- Daily limit checks added
- Unlogged profiles marked with "!" (auto-updates)
- Updated agent wait system
- Partial file and code restructuring

## [v1.1] - 14th September 2025
- Fixed global stop bug: closing one profile no longer stops all tabs
- Fixed request bug: subsequent runs now send requests properly
