# mlearned

This is a toy project to predict match-day performance for friends in Learned League.

# Setup

I'm running using Python 3.12.0 on Mac OS X with pyenv for environment management.
You can find instructions for installing pyenv [here](https://github.com/pyenv/pyenv).

With pyenv installed, make sure you have 3.12.0 on your machine by running `$ pyenv versions`.
If you don't, install it with `$ pyenv install 3.12.0`, and then you can configure the directory
where you'll be running this tool to rely on it:

```
$ cd /dir/where/you/will/run/tool
$ pyenv local 3.12.0
```

You'll also need to install playwright. Do this _after_ you've created your environment.

```
$ pip3 install playwright
$ playright install
```

# Credentials

The tool expects that you have two environment variables defined.

- `LL_USER`: Your LearnedLeague username.
- `LL_PASS`: Your LearnedLeague password.

# friends.json

The tool expects that you have a file named `friends.json` in the same directory, for all of the friends who you want to make predictions for.

The structure expected is below, mapping LearnedLeague user IDs to human-readable names.

```json
{
  "12345": { "name": "Foo Friendly" },
  "23456": { "name": "Bar Friendo" },
  "34567": { "name": "Baz Friender" }
}
```
