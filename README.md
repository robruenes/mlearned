# mlearned

This is a toy project to predict match-day performance for friends in Learned League.

This repo currently includes a utility to scrape data from LearnedLeague (`scrape_learned_league.py`),
and a script to predict the current match day's categories (`predict_categories.py`) by feeding
the question text to Google's Gemini LLM and asking it to choose the correct category.

Down the road, the prediction model will be included too.

In the spirit of Learned League: inspecting the LLM's question category output for
a current match day is _absolutely_ cheating and must be avoided by anyone relying
on this tool :)

# Setup

I'm running using Python 3.11.0 on Mac OS X with pyenv for environment management.
You can find instructions for installing pyenv [here](https://github.com/pyenv/pyenv).

With pyenv installed, make sure you have 3.11.0 on your machine by running `$ pyenv versions`.
If you don't, install it with `$ pyenv install 3.11.0`, and then you can configure the directory
where you'll be running this tool to rely on it:

```zsh
$ cd /dir/where/you/will/run/tool
$ pyenv local 3.11.0
```

You'll also need to install a few dependencies. Do this _after_ you've created your environment.

```zsh
$ pip3 install colorama
$ pip3 install pyarrow
$ pip3 install lxml
$ pip3 install html5lib
$ pip3 install pandas
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

The scraper expects a JSON file containing players of interest in the following format, mapping LearnedLeague user IDs to human-readable names.

```json
{
  "12345": { "name": "Foo Friendly" },
  "23456": { "name": "Bar Friendo" },
  "34567": { "name": "Baz Friendmeinster" }
}
```

By default, it expects it to be named `friends.json` and located in the same directory, but this can be overridden
using the `-p`/`--players_file` flag.

# branches.json

The scraper can also optionally use a file to scrape all of the players in a given branch, in the same format:

```json
  "12345": { "name": "Branch A" },
  "23456": { "name": "Branch B" },
  "34567": { "name": "Branch C" }
```

You can pass this file to the script by using the `-b`/`--branches_file` flag.

# Scraping data from LL

After following all of the steps above, you can scrape data from Learned League by running:

```zsh
$ python scrape_learned_league.py
```

This will produce one folder for each scraped player in the directory `data/{name}`, along with
files containing the question categories for each season in `data/seasons`.

By default, the script will check for the existence of output files before scraping duplicate
data. To bypass this option and do a full scrape, you can pass the `-s` or `--skip_check_files` flags.
