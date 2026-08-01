import os
import re
import json
import sqlite3
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from backend.models import ArticleResponse, SeedTopic

# Load environment variables
load_dotenv()

# Support Vercel / serverless read-only filesystem by writing SQLite cache to /tmp if needed
LOCAL_DIR = os.path.dirname(__file__)
if os.access(LOCAL_DIR, os.W_OK):
    DB_PATH = os.path.join(LOCAL_DIR, "encarta_cache.db")
else:
    DB_PATH = "/tmp/encarta_cache.db"


def init_db(force_reset: bool = False):
    """Initialize or reset the SQLite cache and knowledge_nodes table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if force_reset:
        cursor.execute("DROP TABLE IF EXISTS article_cache")
        cursor.execute("DROP TABLE IF EXISTS knowledge_nodes")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS article_cache (
            topic TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_nodes (
            id TEXT PRIMARY KEY,
            title TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            era TEXT NOT NULL,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            summary_short TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

    # Populate clean initial seed topics
    seed_initial_nodes_into_db(force_reset)


def seed_initial_nodes_into_db(force_reset: bool = False):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if force_reset:
        cursor.execute("DELETE FROM knowledge_nodes")
        cursor.execute("DELETE FROM article_cache")
        conn.commit()

    cursor.execute("SELECT COUNT(*) FROM knowledge_nodes")
    count = cursor.fetchone()[0]
    
    if count == 0:
        initial_seeds = [
            ("microsoft-encarta", "Microsoft Encarta", "Technology", "1993 – 2009", 47.6405, -122.1297, "The legendary 90s CD-ROM multimedia digital encyclopedia pioneer."),
            ("ancient-rome", "Ancient Rome", "History", "753 BCE – 476 CE", 41.9028, 12.4964, "The colossal empire that pioneered Roman law, roads, and aqueducts."),
            ("byzantine-empire", "Byzantine Empire", "History", "330 CE – 1453 CE", 41.0082, 28.9784, "Constantinople crossroads connecting Western Europe and Silk Road trade."),
            ("silk-road", "The Silk Road", "Trade & Exploration", "130 BCE – 1453 CE", 34.3416, 108.9398, "Ancient transcontinental trade network connecting Asia, Persia, and Europe."),
            ("ancient-persia", "Ancient Persia", "History", "550 BCE – 330 BCE", 29.9352, 52.8906, "Persepolis empire linking Silk Road, Mesopotamia, and Mediterranean."),
            ("age-of-discovery", "Age of Discovery", "Trade & Exploration", "1400 – 1700", 38.7223, -9.1393, "Global maritime exploration linking Silk Road routes to the Americas."),
            ("silicon-valley", "Silicon Valley", "Technology", "1939 – Present", 37.3875, -122.0575, "Global epicenter of microchip innovation, personal computing, and AI."),
            ("quantum-physics", "Quantum Physics", "Science", "1900 – Present", 52.5200, 13.4050, "The subatomic physics revolution of wave-particle duality and entanglement."),
            ("renaissance-florence", "Renaissance Florence", "Art & Culture", "1300 – 1600", 43.7696, 11.2558, "Cradle of humanism, perspective painting, and Medici patronage."),
            ("industrial-revolution", "Industrial Revolution", "Technology", "1760 – 1840", 53.4808, -2.2426, "Mechanization, steam locomotives, and urban factory transformation."),
            ("ancient-egypt", "Ancient Egypt", "History", "3100 BCE – 30 BCE", 29.9792, 31.1342, "Pyramids of Giza, hieroglyphics, and Pharaohs along the Nile."),
            ("space-exploration", "Space Exploration", "Science", "1957 – Present", 28.5721, -80.6480, "Sputnik, Apollo Moon landings, Mars rovers, and cosmic telescopes.")
        ]
        cursor.executemany("""
            INSERT OR IGNORE INTO knowledge_nodes (id, title, category, era, lat, lng, summary_short)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, initial_seeds)
        conn.commit()
    conn.close()


# Ensure DB table exists on module load
init_db(force_reset=False)


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
    """Save article JSON dictionary and persist node into SQLite database."""
    normalized_key = topic.strip().lower()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT OR REPLACE INTO article_cache (topic, data) VALUES (?, ?)",
        (normalized_key, json.dumps(article_dict))
    )

    try:
        title = article_dict.get("title", topic.strip().title())
        node_id = re.sub(r'\s+', '-', title.strip().lower())
        category = article_dict.get("category", "Knowledge Node")
        era = article_dict.get("era", "Historical Epoch")
        coords = article_dict.get("coordinates", {})
        lat = float(coords.get("lat", 20.0 + (hash(title) % 50)))
        lng = float(coords.get("lng", (hash(title * 2) % 360) - 180))
        summary = article_dict.get("summary", "")
        summary_short = summary[:110] + "..." if len(summary) > 110 else summary

        cursor.execute("""
            INSERT OR REPLACE INTO knowledge_nodes (id, title, category, era, lat, lng, summary_short)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (node_id, title, category, era, lat, lng, summary_short))
    except Exception as err:
        print(f"[SQLite Node Persistence Warning] {err}")

    conn.commit()
    conn.close()


def get_all_nodes() -> List[Dict[str, Any]]:
    """Fetch all persistent knowledge nodes from SQLite DB."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, category, era, lat, lng, summary_short FROM knowledge_nodes ORDER BY created_at ASC")
    rows = cursor.fetchall()
    conn.close()

    nodes = []
    for r in rows:
        nodes.append({
            "id": r[0],
            "title": r[1],
            "category": r[2],
            "era": r[3],
            "lat": r[4],
            "lng": r[5],
            "summary_short": r[6]
        })
    return nodes


# Comprehensive Pre-baked Seed Topics Fixtures
PREBAKED_FIXTURES: Dict[str, Dict[str, Any]] = {
    "microsoft encarta": {
        "title": "Microsoft Encarta",
        "category": "Technology",
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
            }
        ],
        "related_topics": ["Silicon Valley", "Ancient Rome", "Quantum Physics", "Renaissance Florence"]
    },
    "the silk road": {
        "title": "The Silk Road",
        "category": "Trade & Exploration",
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
            }
        ],
        "related_topics": ["Byzantine Empire", "Ancient Persia", "Age of Discovery", "Ancient Rome"]
    },
    "byzantine empire": {
        "title": "Byzantine Empire",
        "category": "History",
        "era": "330 CE – 1453 CE",
        "wiki_query": "Byzantine_Empire",
        "coordinates": {"lat": 41.0082, "lng": 28.9784},
        "summary": "The Byzantine Empire was the continuation of the Roman Empire in its eastern provinces during Late Antiquity and the Middle Ages. Centered at Constantinople (modern Istanbul), it served as the crucial bridge connecting European civilization to the Silk Road trade network.",
        "milestones": [
            {"year": "330 CE", "event": "Constantine the Great dedicates Constantinople as the new capital of the Roman Empire."},
            {"year": "537 CE", "event": "Emperor Justinian I completes the Hagia Sophia cathedral."}
        ],
        "trivia": "Constantinople's massive triple-layered Theodosian Walls repelled invasions for over 1,000 years!",
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
        "category": "History",
        "era": "550 BCE – 330 BCE",
        "wiki_query": "Achaemenid_Empire",
        "coordinates": {"lat": 29.9352, "lng": 52.8906},
        "summary": "Ancient Persia under the Achaemenid Empire was the first global superpower, spanning from Egypt and Greece to India. With monumental capitals like Persepolis and the 2,500 km Royal Road, Persia established the foundational trade infrastructure later absorbed into the Silk Road.",
        "milestones": [
            {"year": "550 BCE", "event": "Cyrus the Great founds the Achaemenid Persian Empire."}
        ],
        "trivia": "Darius the Great established the Chapar Khaneh, the world's first organized postal system using relay stations across the Royal Road!",
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
        "category": "Trade & Exploration",
        "era": "1400 – 1700",
        "wiki_query": "Age_of_Discovery",
        "coordinates": {"lat": 38.7223, "lng": -9.1393},
        "summary": "The Age of Discovery was a period of extensive European overseas exploration that bridged the medieval Silk Road to global maritime trade. Driven by naval advancements, explorers established direct ocean trade routes connecting Europe, Asia, Africa, and the Americas.",
        "milestones": [
            {"year": "1498", "event": "Vasco da Gama sails around Africa to reach India, establishing maritime Silk Road access."}
        ],
        "trivia": "Navigational instruments like the astrolabe and magnetic compass were brought to Western Europe via Silk Road exchanges!",
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
        "category": "History",
        "era": "753 BCE – 476 CE",
        "wiki_query": "Ancient_Rome",
        "coordinates": {"lat": 41.9028, "lng": 12.4964},
        "summary": "Ancient Rome evolved from an iron-age agrarian settlement on the Italian Peninsula into one of the largest and most powerful empires in world history. Roman contributions to law, governance, architecture, engineering, roads, and language continue to shape modern Western civilization.",
        "milestones": [
            {"year": "753 BCE", "event": "Legendary founding of Rome by Romulus and Remus."},
            {"year": "509 BCE", "event": "Establishment of the Roman Republic after overthrowing the monarchy."},
            {"year": "27 BCE", "event": "Augustus becomes the first Roman Emperor, founding the Principate."},
            {"year": "80 CE", "event": "Completion of the Colosseum under Emperor Titus."}
        ],
        "trivia": "The Romans used volcanic ash and seawater to create pozzolana concrete that could harden underwater!",
        "mindmaze_questions": [
            {
                "question": "Which legendary twin brothers were credited with founding the city of Rome in 753 BCE?",
                "options": ["Romulus and Remus", "Castor and Pollux", "Achilles and Hector", "Caesar and Pompey"],
                "correct_index": 0,
                "hint": "They were famously raised by a she-wolf (Lupa)."
            }
        ],
        "related_topics": ["Renaissance Florence", "Industrial Revolution", "The Silk Road", "Ancient Egypt"]
    },
    "silicon valley": {
        "title": "Silicon Valley",
        "category": "Technology",
        "era": "1939 – Present",
        "wiki_query": "Silicon_Valley",
        "coordinates": {"lat": 37.3875, "lng": -122.0575},
        "summary": "Silicon Valley, located in the southern San Francisco Bay Area, is the global epicenter for technology, venture capital, and digital innovation. Named after the silicon semiconductor chip manufacturers of the mid-20th century, it gave birth to personal computing, the internet economy, and artificial intelligence.",
        "milestones": [
            {"year": "1939", "event": "Bill Hewlett and Dave Packard found HP in a Palo Alto garage."},
            {"year": "1976", "event": "Steve Jobs and Steve Wozniak unveil Apple I at the Homebrew Computer Club."},
            {"year": "1998", "event": "Larry Page and Sergey Brin launch Google from a Menlo Park garage."}
        ],
        "trivia": "HP's original garage at 367 Addison Avenue in Palo Alto is recognized as the 'Birthplace of Silicon Valley'.",
        "mindmaze_questions": [
            {
                "question": "Why did the region acquire the nickname 'Silicon Valley'?",
                "options": ["Abundant silicon mining", "Semiconductor chip manufacturing", "Glass production factories", "Solar panel farms"],
                "correct_index": 1,
                "hint": "Silicon is the fundamental element used to produce microchips."
            }
        ],
        "related_topics": ["Quantum Physics", "Industrial Revolution", "Space Exploration", "Microsoft Encarta"]
    },
    "quantum physics": {
        "title": "Quantum Physics",
        "category": "Science",
        "era": "1900 – Present",
        "wiki_query": "Quantum_mechanics",
        "coordinates": {"lat": 52.5200, "lng": 13.4050},
        "summary": "Quantum Physics is the fundamental branch of physics that explores the behavior of energy and matter at atomic and subatomic scales. Revealing phenomena such as wave-particle duality, quantum superposition, and entanglement, it forms the foundation for lasers, semiconductors, and quantum computing.",
        "milestones": [
            {"year": "1900", "event": "Max Planck proposes energy quantization to explain black-body radiation."},
            {"year": "1905", "event": "Albert Einstein explains the photoelectric effect using light quanta (photons)."}
        ],
        "trivia": "Schrödinger's cat thought experiment was created to illustrate how absurd quantum superposition seemed when applied to macroscopic objects!",
        "mindmaze_questions": [
            {
                "question": "Who introduced energy quantization in 1900, starting the quantum revolution?",
                "options": ["Max Planck", "Albert Einstein", "Niels Bohr", "Isaac Newton"],
                "correct_index": 0,
                "hint": "He gave his name to Planck's constant (h)."
            }
        ],
        "related_topics": ["Silicon Valley", "Industrial Revolution", "Space Exploration"]
    },
    "renaissance florence": {
        "title": "Renaissance Florence",
        "category": "Art & Culture",
        "era": "1300 – 1600",
        "wiki_query": "Florence",
        "coordinates": {"lat": 43.7696, "lng": 11.2558},
        "summary": "Florence, Italy, was the cradle of the Italian Renaissance. Backed by wealthy merchant patrons like the Medici family, Florence fostered unprecedented revivals in classical humanism, perspective painting, sculpture, and architecture under masters like Leonardo da Vinci and Michelangelo.",
        "milestones": [
            {"year": "1436", "event": "Brunelleschi completes the dome of Santa Maria del Fiore."},
            {"year": "1504", "event": "Michelangelo unveils the statue of David."}
        ],
        "trivia": "Brunelleschi constructed the Florence Cathedral dome without wooden scaffolding support structure!",
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
        "category": "Technology",
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
    },
    "ancient egypt": {
        "title": "Ancient Egypt",
        "category": "History",
        "era": "3100 BCE – 30 BCE",
        "wiki_query": "Ancient_Egypt",
        "coordinates": {"lat": 29.9792, "lng": 31.1342},
        "summary": "Ancient Egypt was a civilization of ancient North Africa along the lower reaches of the Nile River. Famous for the Great Pyramids of Giza, hieroglyphic writing, papyrus, and monumental pharaonic architecture.",
        "milestones": [
            {"year": "3100 BCE", "event": "Unification of Upper and Lower Egypt under King Menes."},
            {"year": "2560 BCE", "event": "Completion of the Great Pyramid of Giza under Pharaoh Khufu."},
            {"year": "1323 BCE", "event": "Burial of Pharaoh Tutankhamun in the Valley of the Kings."}
        ],
        "trivia": "The Great Pyramid of Giza was the tallest man-made structure in the world for over 3,800 years!",
        "mindmaze_questions": [
            {
                "question": "Which river sustained ancient Egyptian civilization?",
                "options": ["Nile River", "Amazon River", "Tigris River", "Euphrates River"],
                "correct_index": 0,
                "hint": "It flows northwards through Africa into the Mediterranean Sea."
            }
        ],
        "related_topics": ["Ancient Persia", "Ancient Rome", "The Silk Road"]
    },
    "space exploration": {
        "title": "Space Exploration",
        "category": "Science",
        "era": "1957 – Present",
        "wiki_query": "Space_exploration",
        "coordinates": {"lat": 28.5721, "lng": -80.6480},
        "summary": "Space Exploration is the discovery and exploration of celestial structures in outer space by means of evolving space technology. From Sputnik and the Apollo Moon landings to Mars rovers and the James Webb Space Telescope.",
        "milestones": [
            {"year": "1957", "event": "Soviet Union launches Sputnik 1, the first artificial Earth satellite."},
            {"year": "1969", "event": "Apollo 11 lands Neil Armstrong and Buzz Aldrin on the Moon."},
            {"year": "2021", "event": "James Webb Space Telescope launches to uncover early universe galaxies."}
        ],
        "trivia": "Footprints left on the Moon by Apollo astronauts will remain intact for millions of years because there is no wind or water erosion!",
        "mindmaze_questions": [
            {
                "question": "In what year did the Apollo 11 mission successfully land humans on the Moon?",
                "options": ["1969", "1957", "1975", "1981"],
                "correct_index": 0,
                "hint": "One small step for man, one giant leap for mankind."
            }
        ],
        "related_topics": ["Quantum Physics", "Silicon Valley", "Industrial Revolution"]
    }
}


def generate_fallback_mock(topic: str) -> Dict[str, Any]:
    """Generate dynamic structured mock article payload for unknown search queries in mock mode."""
    clean_topic = topic.strip().title()
    
    category = "History"
    lower_t = clean_topic.lower()
    if any(k in lower_t for k in ["tech", "computer", "ai", "robot", "code", "cyber", "digital", "data", "software"]):
        category = "Technology"
    elif any(k in lower_t for k in ["physics", "space", "astro", "bio", "chem", "quantum", "gene", "science", "planet"]):
        category = "Science"
    elif any(k in lower_t for k in ["art", "music", "paint", "sculpt", "literature", "philosophy", "theatre", "culture"]):
        category = "Art & Culture"
    elif any(k in lower_t for k in ["road", "trade", "route", "expedition", "sea", "ocean", "navy", "voyage"]):
        category = "Trade & Exploration"

    return {
        "title": clean_topic,
        "category": category,
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
                "options": [f"{category} & Innovation", "Space Travel", "Undersea Exploration", "Particle Physics"],
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
        "related_topics": ["Microsoft Encarta", "Silicon Valley", "Quantum Physics", "The Silk Road"]
    }


def generate_node_structure_with_gemma(topic: str, client, types) -> Dict[str, Any]:
    """
    Call gemma-4-31b with High Thinking to create the node structure from the topic & article details.
    """
    prompt = f"""
You are the knowledge engine for 'Encarta 2.0 (NewGen Retro Edition)'.
Analyze the topic/article: '{topic}'.

Return ONLY a single valid JSON object adhering strictly to this node structure:
{{
  "title": "{topic.strip().title()}",
  "category": "<History, Technology, Science, Art & Culture, or Trade & Exploration>",
  "era": "<Historical era / years>",
  "wiki_query": "<exact Wikipedia article title string>",
  "coordinates": {{"lat": <float -90 to 90>, "lng": <float -180 to 180>}},
  "summary": "<2-3 sentence engaging educational summary>",
  "milestones": [
    {{"year": "<year/date>", "event": "<description of key milestone event>"}},
    {{"year": "<year/date>", "event": "<description of key milestone event>"}},
    {{"year": "<year/date>", "event": "<description of key milestone event>"}}
  ],
  "trivia": "<Fascinating 'Did You Know?' trivia fact>",
  "related_topics": ["<Related Topic 1>", "<Related Topic 2>", "<Related Topic 3>"]
}}
"""
    models = ["gemma-4-31b", "gemini-2.5-flash"]
    for m in models:
        try:
            config_kwargs = {"response_mime_type": "application/json"}
            if hasattr(types, "ThinkingConfig"):
                try:
                    config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=2048)
                except Exception:
                    pass

            config = types.GenerateContentConfig(**config_kwargs)
            response = client.models.generate_content(
                model=m,
                contents=prompt,
                config=config
            )
            return json.loads(response.text.strip())
        except Exception as err:
            print(f"[Gemma Node Structure Warning] Model {m} failed: {err}. Attempting next model...")

    return generate_fallback_mock(topic)


def generate_quiz_with_flash(topic: str, summary: str, client, types) -> List[Dict[str, Any]]:
    """
    Call gemini-2.5-flash dedicated for MindMaze trivia dungeon quiz generation.
    """
    prompt = f"""
Generate 3 engaging trivia questions for the MindMaze dungeon game for topic '{topic}'.
Context: {summary}

Return ONLY a single valid JSON array:
[
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
  }},
  {{
    "question": "<Decipher the clue trivia question text>",
    "options": ["<Option A>", "<Option B>", "<Option C>", "<Option D>"],
    "correct_index": <0, 1, 2, or 3>,
    "hint": "<Helpful hint>"
  }}
]
"""
    try:
        config = types.GenerateContentConfig(response_mime_type="application/json")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=config
        )
        return json.loads(response.text.strip())
    except Exception as err:
        print(f"[Flash Quiz Generation Warning] Flash model quiz generation failed: {err}")
        mock = generate_fallback_mock(topic)
        return mock.get("mindmaze_questions", [])


def get_article(topic: str) -> ArticleResponse:
    """
    Main article retrieval pipeline:
    1. Check SQLite Cache
    2. Check Mock Mode
    3. Use gemma-4-31b with High Thinking to create Node Structure
    4. Use gemini-2.5-flash to generate MindMaze Quiz
    5. Save node into SQLite database & return.
    """
    normalized_key = topic.strip().lower()

    # 1. Check SQLite Cache
    cached_data = get_cached_article(normalized_key)
    if cached_data:
        save_cached_article(topic, cached_data)
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

    # 3. Call LLMs via google-genai SDK
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    # Step 1: Create Node Structure using gemma-4-31b model at High Thinking
    node_data = generate_node_structure_with_gemma(topic, client, types)

    # Step 2: Generate MindMaze Quiz using gemini-2.5-flash model
    quiz_questions = generate_quiz_with_flash(topic, node_data.get("summary", ""), client, types)
    node_data["mindmaze_questions"] = quiz_questions

    # Save to SQLite database (article_cache & knowledge_nodes tables)
    save_cached_article(topic, node_data)
    return ArticleResponse(**node_data)
