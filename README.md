# mlearned

This is a toy project to predict match-day performance for friends in Learned League.

# Setup

I'm running using Python 3.11.0 on Mac OS X with pyenv for environment management.
You can find instructions for installing pyenv [here](https://github.com/pyenv/pyenv).

With pyenv installed, make sure you have 3.11.0 on your machine by running `$ pyenv versions`.
If you don't, install it with `$ pyenv install 3.11.0`, and then you can configure the directory
where you'll be running this tool to rely on it:

```
$ cd /dir/where/you/will/run/tool
$ pyenv local 3.11.0
```

You'll also need to install a few dependencies. Do this _after_ you've created your environment.

```
$ pip3 install colorama
$ pip3 install pyarrow
$ pip3 install pandas
$ pip3 install lxml
$ pip3 install google-generativeai
$ pip3 install playwright
$ playright install
```

# Credentials

The tool expects that you have a few environment variables defined.

- `LL_USER`: Your LearnedLeague username.
- `LL_PASS`: Your LearnedLeague password.
- `GEMINI_KEY`: An API key for Google's Gemini model, which you can get by following the [instructions here](https://ai.google.dev/tutorials/setup).

# friends.json

The tool expects that you have a file named `friends.json` in the same directory, for all of the friends who you want to make predictions for.

The structure expected is below, mapping LearnedLeague user IDs to human-readable names.

```json
{
  "12345": { "name": "Foo Friendly" },
  "23456": { "name": "Bar Friendo" },
  "34567": { "name": "Baz Friendmeinster" }
}
```

# Scraping data from LL

After following all of the steps above, you can scrape data from Learned League by running `python scrape_friend_data.py`.

# Generating the training set

After data has been scraped, a training set can be produced by running `python generate_training_set.py`, which will produce
a CSV in `data/training_set.csv`.
