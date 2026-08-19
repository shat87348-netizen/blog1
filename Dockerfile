ARG RUBY_IMAGE=docker.m.daocloud.io/library/ruby:3.2.2-bookworm
ARG NGINX_IMAGE=docker.m.daocloud.io/library/nginx:stable

FROM ${RUBY_IMAGE} AS builder

RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY Gemfile Gemfile.lock ./
RUN gem install bundler -v 2.6.9 \
    && bundle install

COPY . .
RUN bundle exec jekyll build

FROM ${NGINX_IMAGE}

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/_site /usr/share/nginx/blog
RUN chmod -R a+rX /usr/share/nginx/blog

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl --fail --silent --show-error --output /dev/null http://127.0.0.1/post.html || exit 1
