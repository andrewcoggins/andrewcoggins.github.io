FROM ruby:2.5

# throw errors if Gemfile has been modified since Gemfile
#RUN bundle config --global frozen 1

COPY Gemfile Gemfile.lock ./

RUN gem install bundler

RUN bundle install

COPY . /app

WORKDIR /app