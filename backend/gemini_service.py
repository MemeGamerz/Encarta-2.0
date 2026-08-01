import os
import json
import sqlite3
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from backend.models import ArticleResponse

# Load environment variables
load_dotenv()

DB_PATH = os.path.join(os.path.dirname(__file__), "encarta_cache.db")


def init_db():
    """Initialize the SQLite cache table if it does not exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS article_cache (
            topic TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


# Ensure DB table exists on module load
init_db()


def get_cached_article(topic: str) -> Optional[Dict[str, Any]]:
    """Retrieve cached article JSON dictionary if present."""
    normalized_key = topic.strip().lower()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT data FROM article_cache WHERE LOWER(topic) = ?", (normalized_key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        try:
            return json.loads(row[0])
        except Exception:
            return None
    return None


def save_cached_article(topic: str, article_dict: Dict[str, Any]):
    """Save article JSON dictionary to SQLite cache using parameterized inputs."""
    normalized_key = topic.strip().lower()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO article_cache (topic, data) VALUES (?, ?)",
        (normalized_key, json.dumps(article_dict))
    )
    conn.commit()
    conn.close()


# Comprehensive Pre-baked Seed Topics Fixtures
PREBAKED_FIXTURES: Dict[str, Dict[str, Any]] = {
    "microsoft encarta": {
        "title": "Microsoft Encarta",
        "era": "1993 – 2009",
        "wiki_query": "Encarta",
        "coordinates": {"lat": 47.6405, "lng": -122.1297},
        "summary": "Microsoft Encarta was a digital multimedia encyclopedia published by Microsoft from 1993 to 2009. Originally released on CD-ROM with interactive 3D globes, sound clips, and MindMaze trivia games, Encarta revolutionized digital education and knowledge exploration for millions of users worldwide.",
        "milestones": [
            {"year": "1993", "event": "Microsoft launches Encarta on CD-ROM based on Funk & Wagnalls encyclopedia."},
            {"year": "1995", "event": "Encarta 95 debuts MindMaze 2D trivia dungeon game and audio sound clips."},
            {"year": "2000", "event": "Encarta Africana and online web encyclopedia search integration introduced."},
            {"year": "2009", "event": "Microsoft discontinues Encarta CD-ROM disc production as Web 2.0 expands."},
            {"year": "2026", "event": "Encarta 2.0 (NewGen Retro Edition) is reborn with 3D WebGL spatial nodes!"}
        ],
        "trivia": "Encarta's iconic MindMaze game was designed to make encyclopedia research addictive by locking castle doors behind historical multiple-choice trivia challenges!",
        "mindmaze_questions": [
            {
                "question": "In what year did Microsoft release the very first edition of Encarta on CD-ROM?",
                "options": ["1993", "1995", "1998", "2001"],
                "correct_index": 0,
                "hint": "It was launched in the early 90s based on Funk & Wagnalls content."
            },
            {
                "question": "What famous 2D trivia dungeon maze game was built directly into classic Encarta?",
                "options": ["MindMaze", "Math Blaster", "Where in the World is Carmen Sandiego?", "Oregon Trail"],
                "correct_index": 0,
                "hint": "Players guided a knight through castle doors by answering encyclopedia trivia."
            },
            {
                "question": "True or False: Encarta 2.0 combines 90s Encarta nostalgia with modern 3D WebGL globes and Gemini AI.",
                "options": ["True", "False"],
                "correct_index": 0,
                "hint": "Encarta 2.0 brings back the retro design system with modern WebGL."
            }
        ],
        "related_topics": ["Silicon Valley", "Ancient Rome", "Quantum Physics", "Renaissance Florence"]
    },
    "the silk road": {
        "title": "The Silk Road",
        "era": "130 BCE – 1453 CE",
        "wiki_query": "Silk_Road",
        "coordinates": {"lat": 34.3416, "lng": 108.9398},
        "summary": "The Silk Road was an ancient network of Eurasian trade routes active from the Han dynasty until the Ottoman Empire boycotted trade with the West in 1453. Spanning over 6,400 kilometers, it facilitated economic, cultural, political, and religious interactions between East Asia, Persia, Arabia, and the Mediterranean.",
        "milestones": [
            {"year": "130 BCE", "event": "Han Dynasty officially opens trade with the West following Zhang Qian's missions."},
            {"year": "600 CE", "event": "Tang Dynasty golden age accelerates silk, paper, and spice exchanges."},
            {"year": "1271 CE", "event": "Marco Polo journeys across the Silk Road to the court of Kublai Khan."},
            {"year": "1453 CE", "event": "Fall of Constantinople prompts European nations to seek maritime sea routes."}
        ],
        "trivia": "Papermaking, gunpowder, printing, and silk production spread from China across the Silk Road to Europe, fundamentally altering world history!",
        "mindmaze_questions": [
            {
                "question": "Which Chinese dynasty officially opened the Silk Road trade routes around 130 BCE?",
                "options": ["Han Dynasty", "Ming Dynasty", "Tang Dynasty", "Qing Dynasty"],
                "correct_index": 0,
                "hint": "Opened following imperial envoy Zhang Qian's western missions."
            },
            {
                "question": "What famous Venetian explorer traveled the Silk Road to China in 1271?",
                "options": ["Marco Polo", "Christopher Columbus", "Vasco da Gama", "Ferdinand Magellan"],
                "correct_index": 0,
                "hint": "He documented his travels in 'The Travels of Marco Polo'."
            }
        ],
        "related_topics": ["Byzantine Empire", "Ancient Persia", "Age of Discovery", "Ancient Rome"]
    },
    "byzantine empire": {
        "title": "Byzantine Empire",
        "era": "330 CE – 1453 CE",
        "wiki_query": "Byzantine_Empire",
        "coordinates": {"lat": 41.0082, "lng": 28.9784},
        "summary": "The Byzantine Empire was the continuation of the Roman Empire in its eastern provinces during Late Antiquity and the Middle Ages. Centered at Constantinople (modern Istanbul), it served as the crucial bridge connecting European civilization to the Silk Road trade network.",
        "milestones": [
            {"year": "330 CE", "event": "Constantine the Great dedicates Constantinople as the new capital of the Roman Empire."},
            {"year": "537 CE", "event": "Emperor Justinian I completes the Hagia Sophia cathedral."},
            {"year": "1453 CE", "event": "Fall of Constantinople to the Ottoman Empire under Sultan Mehmed II."}
        ],
        "trivia": "Constantinople's massive triple-layered Theodosian Walls repelled invasions for over 1,000 years until defeated by gunpowder cannons in 1453!",
        "mindmaze_questions": [
            {
                "question": "What imperial capital city served as the heart of the Byzantine Empire?",
                "options": ["Constantinople", "Rome", "Athens", "Alexandria"],
                "correct_index": 0,
                "hint": "Founded by Emperor Constantine, today known as Istanbul."
            }
        ],
        "related_topics": ["The Silk Road", "Ancient Rome", "Renaissance Florence", "Ancient Persia"]
    },
    "ancient persia": {
        "title": "Ancient Persia",
        "era": "550 BCE – 330 BCE",
        "wiki_query": "Achaemenid_Empire",
        "coordinates": {"lat": 29.9352, "lng": 52.8906},
        "summary": "Ancient Persia under the Achaemenid Empire was the first global superpower, spanning from Egypt and Greece to India. With monumental capitals like Persepolis and the 2,500 km Royal Road, Persia established the foundational trade infrastructure later absorbed into the Silk Road.",
        "milestones": [
            {"year": "550 BCE", "event": "Cyrus the Great founds the Achaemenid Persian Empire."},
            {"year": "515 BCE", "event": "Darius the Great constructs the Royal Road courier network."}
        ],
        "trivia": "Darius the Great established the Chapar Khaneh, the world's first organized postal system using relay stations and fresh horses across the Royal Road!",
        "mindmaze_questions": [
            {
                "question": "Which Persian king founded the Achaemenid Empire in 550 BCE?",
                "options": ["Cyrus the Great", "Darius I", "Xerxes", "Artaxerxes"],
                "correct_index": 0,
                "hint": "Known for issuing the Cyrus Cylinder human rights decree."
            }
        ],
        "related_topics": ["The Silk Road", "Byzantine Empire", "Ancient Egypt", "Ancient Rome"]
    },
    "age of discovery": {
        "title": "Age of Discovery",
        "era": "1400 – 1700",
        "wiki_query": "Age_of_Discovery",
        "coordinates": {"lat": 38.7223, "lng": -9.1393},
        "summary": "The Age of Discovery was a period of extensive European overseas exploration that bridged the medieval Silk Road to global maritime trade. Driven by naval advancements, explorers established direct ocean trade routes connecting Europe, Asia, Africa, and the Americas.",
        "milestones": [
            {"year": "1498", "event": "Vasco da Gama sails around Africa to reach India, establishing maritime Silk Road access."},
            {"year": "1519", "event": "Magellan expedition completes the first circumnavigation of the globe."}
        ],
        "trivia": "Navigational instruments like the astrolabe and magnetic compass were brought to Western Europe via Silk Road exchanges before enabling transoceanic voyages!",
        "mindmaze_questions": [
            {
                "question": "Which Portuguese navigator pioneered the direct ocean route from Europe to India in 1498?",
                "options": ["Vasco da Gama", "Christopher Columbus", "Ferdinand Magellan", "Henry the Navigator"],
                "correct_index": 0,
                "hint": "Sailed around the Cape of Good Hope."
            }
        ],
        "related_topics": ["The Silk Road", "Renaissance Florence", "Industrial Revolution", "Silicon Valley"]
    },
    "ancient rome": {
        "title": "Ancient Rome",
        "era": "753 BCE – 476 CE",
        "wiki_query": "Ancient_Rome",
        "coordinates": {"lat": 41.9028, "lng": 12.4964},
        "summary": "Ancient Rome evolved from an iron-age agrarian settlement on the Italian Peninsula into one of the largest and most powerful empires in world history. Roman contributions to law, governance, architecture, engineering, roads, and language continue to shape modern Western civilization.",
        "milestones": [
            {"year": "753 BCE", "event": "Legendary founding of Rome by Romulus and Remus."},
            {"year": "509 BCE", "event": "Establishment of the Roman Republic after overthrowing the monarchy."},
            {"year": "27 BCE", "event": "Augustus becomes the first Roman Emperor, founding the Principate."},
            {"year": "80 CE", "event": "Completion of the Colosseum under Emperor Titus."},
            {"year": "476 CE", "event": "Fall of the Western Roman Empire following the deposition of Romulus Augustulus."}
        ],
        "trivia": "The Romans used a mixture of volcanic ash, lime, and seawater to create pozzolana concrete that could harden even underwater, allowing structures like the Pantheon dome to endure over 2,000 years!",
        "mindmaze_questions": [
            {
                "question": "Which legendary twin brothers were credited with founding the city of Rome in 753 BCE?",
                "options": ["Romulus and Remus", "Castor and Pollux", "Achilles and Hector", "Caesar and Pompey"],
                "correct_index": 0,
                "hint": "They were famously raised by a she-wolf (Lupa)."
            },
            {
                "question": "True or False: The Colosseum was built primarily for naval sea battle reenactments and gladiator contests.",
                "options": ["True", "False"],
                "correct_index": 0,
                "hint": "It could be flooded with water for mock naval battles!"
            },
            {
                "question": "Decipher the Clue: First Emperor of Rome, adopted son of Julius Caesar, formerly named Octavian.",
                "options": ["Emperor Augustus", "Nero", "Tiberius", "Caligula"],
                "correct_index": 0,
                "hint": "Augustus Caesar ushered in the Pax Romana."
            }
        ],
        "related_topics": ["Renaissance Florence", "Industrial Revolution", "The Silk Road", "Ancient Egypt"]
    },
    "silicon valley": {
        "title": "Silicon Valley",
        "era": "1939 – Present",
        "wiki_query": "Silicon_Valley",
        "coordinates": {"lat": 37.3875, "lng": -122.0575},
        "summary": "Silicon Valley, located in the southern San Francisco Bay Area, is the global epicenter for technology, venture capital, and digital innovation. Named after the silicon semiconductor chip manufacturers of the mid-20th century, it gave birth to personal computing, the internet economy, and artificial intelligence.",
        "milestones": [
            {"year": "1939", "event": "Bill Hewlett and Dave Packard found HP in a Palo Alto garage."},
            {"year": "1956", "event": "William Shockley establishes Shockley Semiconductor Laboratory in Mountain View."},
            {"year": "1976", "event": "Steve Jobs and Steve Wozniak unveil Apple I at the Homebrew Computer Club."},
            {"year": "1998", "event": "Larry Page and Sergey Brin launch Google from a Menlo Park garage."},
            {"year": "2023", "event": "Generative AI boom accelerates research across Silicon Valley labs."}
        ],
        "trivia": "HP's original garage at 367 Addison Avenue in Palo Alto is officially recognized by California state historical landmark #975 as the 'Birthplace of Silicon Valley'.",
        "mindmaze_questions": [
            {
                "question": "Why did the region acquire the nickname 'Silicon Valley'?",
                "options": ["Abundant silicon mining", "Semiconductor chip manufacturing", "Glass production factories", "Solar panel farms"],
                "correct_index": 1,
                "hint": "Silicon is the fundamental element used to produce microchips."
            },
            {
                "question": "Which company was famously started in a Palo Alto garage in 1939?",
                "options": ["Apple", "Hewlett-Packard (HP)", "Google", "Intel"],
                "correct_index": 1,
                "hint": "Founded by Bill Hewlett and Dave Packard."
            }
        ],
        "related_topics": ["Quantum Physics", "Industrial Revolution", "Space Exploration"]
    },
    "quantum physics": {
        "title": "Quantum Physics",
        "era": "1900 – Present",
        "wiki_query": "Quantum_mechanics",
        "coordinates": {"lat": 52.5200, "lng": 13.4050},
        "summary": "Quantum Physics is the fundamental branch of physics that explores the behavior of energy and matter at atomic and subatomic scales. Revealing phenomena such as wave-particle duality, quantum superposition, and entanglement, it forms the foundation for lasers, semiconductors, and quantum computing.",
        "milestones": [
            {"year": "1900", "event": "Max Planck proposes energy quantization to explain black-body radiation."},
            {"year": "1905", "event": "Albert Einstein explains the photoelectric effect using light quanta (photons)."},
            {"year": "1926", "event": "Schrödinger formulates wave mechanics; Heisenberg introduces Uncertainty Principle."},
            {"year": "2022", "event": "Nobel Prize awarded for quantum entanglement experiments."}
        ],
        "trivia": "Schrödinger's famous thought experiment involving a cat in a box was created to illustrate how absurd quantum superposition seemed when applied to macroscopic objects!",
        "mindmaze_questions": [
            {
                "question": "Who introduced energy quantization in 1900, starting the quantum revolution?",
                "options": ["Max Planck", "Albert Einstein", "Niels Bohr", "Isaac Newton"],
                "correct_index": 0,
                "hint": "He gave his name to Planck's constant (h)."
            },
            {
                "question": "What principle states that position and momentum cannot be simultaneously measured exactly?",
                "options": ["Exclusion Principle", "Uncertainty Principle", "Superposition Principle", "Relativity"],
                "correct_index": 1,
                "hint": "Formulated by Werner Heisenberg."
            }
        ],
        "related_topics": ["Silicon Valley", "Industrial Revolution", "Space Exploration"]
    },
    "renaissance florence": {
        "title": "Renaissance Florence",
        "era": "1300 – 1600",
        "wiki_query": "Florence",
        "coordinates": {"lat": 43.7696, "lng": 11.2558},
        "summary": "Florence, Italy, was the cradle of the Italian Renaissance. Backed by wealthy merchant patrons like the Medici family, Florence fostered unprecedented revivals in classical humanism, perspective painting, sculpture, and architecture under masters like Leonardo da Vinci and Michelangelo.",
        "milestones": [
            {"year": "1348", "event": "Social shifts toward humanism following the plague."},
            {"year": "1436", "event": "Brunelleschi completes the dome of Santa Maria del Fiore."},
            {"year": "1504", "event": "Michelangelo unveils the statue of David."}
        ],
        "trivia": "Brunelleschi constructed the Florence Cathedral dome without wooden scaffolding support structure, inventing innovative herringbone bricklaying techniques!",
        "mindmaze_questions": [
            {
                "question": "Which banking family was the chief patron of art in Renaissance Florence?",
                "options": ["Borgia Family", "Medici Family", "Sforza Family", "Visconti Family"],
                "correct_index": 1,
                "hint": "Lorenzo 'the Magnificent' was their leader."
            }
        ],
        "related_topics": ["Ancient Rome", "Industrial Revolution", "The Silk Road"]
    },
    "industrial revolution": {
        "title": "Industrial Revolution",
        "era": "1760 – 1840",
        "wiki_query": "Industrial_Revolution",
        "coordinates": {"lat": 53.4808, "lng": -2.2426},
        "summary": "The Industrial Revolution marked the transition from agrarian, handicraft economies to machine-driven industrial manufacturing. Originating in Great Britain with steam power, textile mechanization, and iron metallurgy, it transformed urban transport and global trade.",
        "milestones": [
            {"year": "1765", "event": "James Watt invents the separate condenser steam engine."},
            {"year": "1804", "event": "Trevithick builds the world's first working steam locomotive."}
        ],
        "trivia": "The word 'sabotage' is rumored to come from French weavers throwing wooden shoes ('sabots') into mechanized looms!",
        "mindmaze_questions": [
            {
                "question": "Which inventor dramatically improved the steam engine with a separate condenser in 1765?",
                "options": ["James Watt", "Thomas Newcomen", "George Stephenson", "Eli Whitney"],
                "correct_index": 0,
                "hint": "The SI unit of power is named after him."
            }
        ],
        "related_topics": ["Silicon Valley", "Ancient Rome", "Renaissance Florence"]
    }
}


def generate_fallback_mock(topic: str) -> Dict[str, Any]:
    """Generate dynamic structured mock article payload for unknown search queries in mock mode."""
    clean_topic = topic.strip().title()
    return {
        "title": clean_topic,
        "era": "Historical & Scientific Epoch",
        "wiki_query": clean_topic.replace(" ", "_"),
        "coordinates": {"lat": 20.0 + (hash(clean_topic) % 50), "lng": (hash(clean_topic * 2) % 360) - 180},
        "summary": f"{clean_topic} represents a crucial landmark in human knowledge and global history. Its impact spans scientific exploration, societal evolution, and technological breakthroughs that continue to inspire researchers worldwide.",
        "milestones": [
            {"year": "Early Origins", "event": f"Foundational discoveries and early developments concerning {clean_topic}."},
            {"year": "Golden Era", "event": f"Widespread adoption, cultural growth, and key innovations in {clean_topic}."},
            {"year": "Modern Age", "event": f"Contemporary applications and lasting legacy of {clean_topic} in modern times."}
        ],
        "trivia": f"Did you know? Scholars continue to uncover fascinating new insights about {clean_topic} in modern archival and scientific research!",
        "mindmaze_questions": [
            {
                "question": f"What key domain is most associated with {clean_topic}?",
                "options": ["Human History & Innovation", "Space Travel", "Undersea Exploration", "Particle Physics"],
                "correct_index": 0,
                "hint": "Consider the foundational impact of this topic on civilization."
            },
            {
                "question": f"True or False: Empirical research on {clean_topic} continues in modern institutions worldwide.",
                "options": ["True", "False"],
                "correct_index": 0,
                "hint": "Research across archives and labs remains active today."
            }
        ],
        "related_topics": ["Ancient Rome", "Silicon Valley", "Quantum Physics", "Renaissance Florence"]
    }


def get_article(topic: str) -> ArticleResponse:
    """
    Main article retrieval with Model Fallback Hierarchy:
    1. SQLite Cache
    2. Check Mock Mode
    3. Primary Model: gemini-2.5-flash (with High Thinking setting)
    4. Secondary Fallback Model: gemini-3.5-flash-lite
    5. Final Fallback: Instant Mock JSON Generator
    """
    normalized_key = topic.strip().lower()

    # 1. Check SQLite Cache
    cached_data = get_cached_article(normalized_key)
    if cached_data:
        return ArticleResponse(**cached_data)

    # 2. Check Mock Mode or missing API Key
    mock_mode = os.getenv("MOCK_MODE", "true").lower() == "true"
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if mock_mode or not api_key:
        if normalized_key in PREBAKED_FIXTURES:
            data = PREBAKED_FIXTURES[normalized_key]
        else:
            data = generate_fallback_mock(topic)
        save_cached_article(topic, data)
        return ArticleResponse(**data)

    # 3. Model Fallback Chain using google-genai SDK
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    prompt = f"""
You are the knowledge engine for 'Encarta 2.0 (NewGen Retro Edition)'.
Provide an in-depth, accurate article payload for the topic: '{topic}'.

Return ONLY a single valid JSON object adhering strictly to this format:
{{
  "title": "{topic.strip().title()}",
  "era": "<Historical era / years>",
  "wiki_query": "<exact Wikipedia article title string, e.g. Ancient_Rome>",
  "coordinates": {{"lat": <float -90 to 90>, "lng": <float -180 to 180>}},
  "summary": "<2-3 sentence engaging educational summary>",
  "milestones": [
    {{"year": "<year/date>", "event": "<description of key milestone event>"}},
    {{"year": "<year/date>", "event": "<description of key milestone event>"}},
    {{"year": "<year/date>", "event": "<description of key milestone event>"}}
  ],
  "trivia": "<Fascinating 'Did You Know?' trivia fact>",
  "mindmaze_questions": [
    {{
      "question": "<Multiple choice trivia question text>",
      "options": ["<Option A>", "<Option B>", "<Option C>", "<Option D>"],
      "correct_index": <0, 1, 2, or 3>,
      "hint": "<Helpful hint>"
    }},
    {{
      "question": "<True or False trivia question text>",
      "options": ["True", "False"],
      "correct_index": <0 or 1>,
      "hint": "<Helpful hint>"
    }}
  ],
  "related_topics": ["<Related Topic 1>", "<Related Topic 2>", "<Related Topic 3>"]
}}
"""

    models_to_try = [
        ("gemini-2.5-flash", True),        # Primary model with thinking budget
        ("gemini-3.5-flash-lite", False)   # Secondary fallback model
    ]

    for model_name, use_thinking in models_to_try:
        try:
            config_kwargs = {"response_mime_type": "application/json"}
            if use_thinking and hasattr(types, "ThinkingConfig"):
                try:
                    config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=2048)
                except Exception:
                    pass

            config = types.GenerateContentConfig(**config_kwargs)
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config
            )

            response_text = response.text.strip()
            data = json.loads(response_text)
            save_cached_article(topic, data)
            return ArticleResponse(**data)

        except Exception as err:
            print(f"[Gemini Fallback Warning] Model {model_name} failed: {err}. Attempting next tier...")

    # 5. Final Fallback to Mock Generator
    print("[Gemini Fallback] All API models failed or rate-limited. Serving instant mock payload.")
    if normalized_key in PREBAKED_FIXTURES:
        data = PREBAKED_FIXTURES[normalized_key]
    else:
        data = generate_fallback_mock(topic)
    save_cached_article(topic, data)
    return ArticleResponse(**data)
