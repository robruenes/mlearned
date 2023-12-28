import os
import google.generativeai as genai

genai.configure(api_key=os.environ["GEMINI_KEY"])


def predict_categories(questions):
    # Set up the model
    generation_config = {
        "temperature": 0,
        "top_p": 1,
        "top_k": 1,
        "max_output_tokens": 2048,
    }

    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
        },
    ]

    prompt_fmt = """
      I am going to provide you with a trivia question and a list of potential question categories (with abbreviations). 
      I would like you to output the category abbreviation that the question belongs to. 
      A question can only belong to a single category. The list of categories and abbreviations is as follows:
        - American History - AMER HIST
        - Art - ART
        - Business and Economics - BUS/ECON
        - Classical Music - CLASS MUSIC
        - Current Events - CURR EVENTS
        - Film and Movies - FILM
        - Food and Drink - FOOD/DRINK
        - Games and Sports - GAMES/SPORT
        - Geography - GEOGRAPHY
        - Language - LANGUAGE
        - Lifestyle - LIFESTYLE
        - Literature - LITERATURE
        - Math - MATH
        - Pop Music - POP MUSIC
        - Science - SCIENCE
        - Television - TELEVISION
        - Theatre - THEATRE
        - World Hist - WORLD HIST

      Please output the category for the following question: "{question}"
    """

    model = genai.GenerativeModel(
        model_name="gemini-pro",
        generation_config=generation_config,
        safety_settings=safety_settings,
    )

    convo = model.start_chat(
        history=[
            {
                "role": "user",
                "parts": prompt_fmt.format(
                    question="The ideal of humanity found in Friedrich Nietzsche's Thus Spake Zarathustra, when translated into English, is the title of an unrelated movie from 1978. What is that word, which also appears in the titles of numerous other works in film and other media?"
                ),
            },
            {"role": "model", "parts": "LITERATURE"},
            {
                "role": "user",
                "parts": prompt_fmt.format(
                    question="Audio, The Complex, and THREE are music albums by what ultramarine performance art ensemble, which has been resident off-Broadway in New York since 1991?"
                ),
            },
            {"role": "model", "parts": "THEATRE"},
            {
                "role": "user",
                "parts": prompt_fmt.format(
                    question="Now commonly used to mean waste or something old, discarded, or of poor quality, what word also once referred to a type of Chinese sailing ship that—belying the current definition—included the most sophisticated and seaworthy ships in the world in the 15th century?"
                ),
            },
            {"role": "model", "parts": "LANGUAGE"},
            {
                "role": "user",
                "parts": prompt_fmt.format(
                    question="What is the name (or abbreviation) of the unit for measuring heat in which the temperature of one pound of water is raised by one degree Fahrenheit?"
                ),
            },
            {"role": "model", "parts": "SCIENCE"},
            {
                "role": "user",
                "parts": prompt_fmt.format(
                    question="Today, the Big Three automakers in the United States are Ford, General Motors, and what other company, the result of a 2021 merger between the PSA Group (aka Peugeot) and the Fiat Chrysler conglomerate?"
                ),
            },
            {"role": "model", "parts": "BUS/ECON"},
            {
                "role": "user",
                "parts": prompt_fmt.format(
                    question="The name of what strongman completes a list that also includes Jackie, Jermaine, Marlon, and Michael?"
                ),
            },
            {"role": "model", "parts": "POP MUSIC"},
            {
                "role": "user",
                "parts": prompt_fmt.format(
                    question="Throughout the 1980s, in millions of American homes one could find a handheld device on which was printed the name 'Jerrold'. What was this device?"
                ),
            },
            {"role": "model", "parts": "TELEVISION"},
            {
                "role": "user",
                "parts": prompt_fmt.format(
                    question="A 1642 group portrait of the militia company of Captain Frans Banninck Cocq and of Lieutenant Willem van Ruytenburch is best known today by what name?"
                ),
            },
            {"role": "model", "parts": "ART"},
            {
                "role": "user",
                "parts": prompt_fmt.format(
                    question="What term used to describe the cohort of women and men who came of age from around World War I to the Great Depression was reportedly coined by Gertrude Stein, and popularized via a frequently recounted conversation with Ernest Hemingway, whose own early works were prototypes for writers of this group?"
                ),
            },
            {"role": "model", "parts": "LITERATURE"},
            {
                "role": "user",
                "parts": prompt_fmt.format(
                    question="Ocean of wisdom is a frequently cited colloquial translation for what Mongolian-language (or partially Mongolian) phrase, and person?"
                ),
            },
            {"role": "model", "parts": "WORLD HIST"},
            {
                "role": "user",
                "parts": prompt_fmt.format(
                    question="The dog who was recently banished from the White House after a series of biting incidents has a name that might suggest he is a member of a local sports team (though he isn't). What is this German Shepherd's name?"
                ),
            },
            {"role": "model", "parts": "CURR EVENTS"},
            {
                "role": "user",
                "parts": prompt_fmt.format(
                    question="According to one story in Greek mythology, what sprang from the body of Medusa upon her death at the hands of Perseus, and was later captured by Bellerophon, helping him defeat the hybrid Chimera? (Proper name required.)",
                ),
            },
            {"role": "model", "parts": "LIFESTYLE"},
        ]
    )

    def extract_category(question):
        convo.send_message(prompt_fmt.format(question=question))
        return convo.last.text

    return [extract_category(question) for question in questions]


### For testing
if __name__ == "__main__":
    test_questions = [
        # Expected: GEOGRAPHY
        "Of the various geographical entities across the world whose names begin with 'New', which one is a territory in the South Pacific Ocean named after most of the land area that is now the country of Scotland?",
        # Expected: MATH
        "In the linear equation with the general form y = mx + b, what word is typically used to indicate what is represented by m?",
        # Expected: GAMES/SPORT
        "While the pitching staff of the 1948 World Series-winning Cleveland Indians featured mound virtuoso Bob Feller and fellow Hall of Famer Bob Lemon, it also famously included what other legend and future Hall of Fame inductee, who had made his professional debut 22 years earlier with the Chattanooga Black Lookouts?",
        # Expected: FOOD/DRINK
        "A dish widely recognized as the national dish of Mexico is a mole that originated in and is named after what Mexican state (as is the pepper that provides a main ingredient)? The state's capital city is a settlement that sits on Mexican Federal Highway 150D between Mexico City and the Atlantic port of Veracruz. Note, name the state (or the capital city, which has the same name).",
        # Expected: LIFESTYLE
        "Derived from a German word for a particular type of educational institution, what four-letter word is Yiddish for synagogue?",
    ]
    print(predict_categories(test_questions))
