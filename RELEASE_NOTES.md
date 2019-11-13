# ID Mapping Service release notes

## 0.1.1

* Updated `pymongo` to fix mongo authentication issues
  * Note that `pymongo 3.9.0+` cannot be pinned until all MongoDB servers are running WiredTiger
    or a config option is added to turn off write retries.

## 0.1.0

* Initial release