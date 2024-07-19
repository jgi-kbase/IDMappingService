# ID Mapping Service release notes

## 0.1.2
* The MongoDB clients have been updated to the most recent version and the service tested against Mongo 7.
* Added id mapping service container test in GHA
* Added the mongo-retrywrites configuration setting in deployment.cfg.templ and deploy.cfg.example, defaulting to false.
* Updated the docker-compose file to start a id mapping service server.
* Added pipenv to handle dependencies.
* Added Dependabot, CodeQL, and release image build.
* Replaced Travis CI with GitHub Actions workflows.
* Updated Python to 3.9.19, Flask to 2.0.0, and werkzeug to 2.0.3

## 0.1.1

* Updated `pymongo` to fix mongo authentication issues
  * Note that `pymongo 3.9.0+` cannot be pinned until all MongoDB servers are running WiredTiger
    or a config option is added to turn off write retries.

## 0.1.0

* Initial release