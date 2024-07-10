FROM kbase/kb_jre:latest as dockerize

FROM python:3.9.19-alpine

# These ARGs values are passed in via the docker build command
ARG BUILD_DATE
ARG VCS_REF
ARG BRANCH=develop

RUN apk add gcc linux-headers libc-dev make git
COPY --from=dockerize /kb/deployment/bin/dockerize /usr/bin/

# install pipenv
RUN pip install --upgrade pip && \
    pip install pipenv

WORKDIR /kb
ADD . /kb

# install deps
RUN pipenv sync --system
RUN make

# The BUILD_DATE value seem to bust the docker cache when the timestamp changes, move to
# the end
LABEL org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.vcs-url="https://github.com/jgikbase/IDMappingService.git" \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.schema-version="1.0.0-rc1" \
      us.kbase.vcs-branch=$BRANCH \
      maintainer="Steve Chan sychan@lbl.gov"

ENV KB_DEPLOYMENT_CONFIG=/kb/deploy.cfg
ENV PYTHONPATH=$PYTHONPATH:/kb/src

ENTRYPOINT [ "/usr/bin/dockerize" ]

# Here are some default params passed to dockerize. They would typically
# be overidden by docker-compose at startup
CMD [ "-template", "/kb/deployment/conf/.templates/deployment.cfg.templ:/kb/deploy.cfg", \
      "-template", "/kb/deployment/conf/.templates/settings.py.templ:/kb/settings.py", \
      "gunicorn", "-c", "/kb/settings.py", "--worker-class", "gevent", \
      "app:app" ]