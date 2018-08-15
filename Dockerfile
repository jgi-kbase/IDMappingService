FROM python:3.6-alpine

# These ARGs values are passed in via the docker build command
ARG BUILD_DATE
ARG VCS_REF
ARG BRANCH=develop


COPY deployment/ /kb/deployment/

# The BUILD_DATE value seem to bust the docker cache when the timestamp changes, move to
# the end
LABEL org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.vcs-url="https://github.com/jgikbase/IDMappingService.git" \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.schema-version="1.0.0-rc1" \
      us.kbase.vcs-branch=$BRANCH \
      maintainer="Steve Chan sychan@lbl.gov"

WORKDIR /kb/module
ENV KB_DEPLOYMENT_CONFIG=/kb/deployment/conf/deployment.cfg
ENV PYTHONPATH=$PYTHONPATH:/kb/module/src

ENTRYPOINT [ "/kb/deployment/bin/dockerize" ]

# TODO DOCKER parameterize the worker count

# Here are some default params passed to dockerize. They would typically
# be overidden by docker-compose at startup
CMD [  "-template", "/kb/deployment/conf/.templates/deployment.cfg.templ:/kb/deployment/conf/deployment.cfg", \
       "gunicorn", "--worker-class", "gevent", "--timeout", "300",
       "--workers", "17", "--bind", ":8080", "app:app" ]
