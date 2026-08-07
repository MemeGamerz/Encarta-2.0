import os
import re
import json
import sqlite3
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from backend.models import ArticleResponse, SeedTopic

# Load environment variables
load_dotenv()

import shutil

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_DB = os.path.join(PROJECT_ROOT, "database.db")

# Vercel / AWS Lambda Serverless Detection:
# In Vercel serverless environments, the deployment directory is strictly read-only.
# We always use /tmp/database.db and copy the bundled database.db into /tmp.
IS_SERVERLESS = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME") or os.getenv("LAMBDA_TASK_ROOT"))

if IS_SERVERLESS or not os.access(PROJECT_ROOT, os.W_OK):
    TMP_DB = "/tmp/database.db"
    try:
        if not os.path.exists(TMP_DB) and os.path.exists(LOCAL_DB):
            shutil.copy2(LOCAL_DB, TMP_DB)
    except Exception as e:
        print(f"[Vercel DB Copy Warning] {e}")
    DB_PATH = TMP_DB
else:
    DB_PATH = LOCAL_DB


def init_db(force_reset: bool = False):
    """Initialize or reset the SQLite cache and knowledge_nodes table."""
    try:
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
    except Exception as err:
        print(f"[DB Initialization Warning] {err}")


def seed_initial_nodes_into_db(force_reset: bool = False):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if force_reset:
        cursor.execute("DELETE FROM knowledge_nodes")
        cursor.execute("DELETE FROM article_cache")
        conn.commit()

    cursor.execute("SELECT COUNT(*) FROM knowledge_nodes")
    count = cursor.fetchone()[0]
    
    if count < len(PREBAKED_FIXTURES):
        for key, data in PREBAKED_FIXTURES.items():
            node_id = re.sub(r'\s+', '-', data['title'].strip().lower())
            summary = data.get('summary', '')
            summary_short = summary[:110] + "..." if len(summary) > 110 else summary
            
            cursor.execute("""
                INSERT OR REPLACE INTO knowledge_nodes (id, title, category, era, lat, lng, summary_short)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                node_id,
                data['title'],
                data['category'],
                data['era'],
                data['coordinates']['lat'],
                data['coordinates']['lng'],
                summary_short
            ))

            cursor.execute("""
                INSERT OR REPLACE INTO article_cache (topic, data)
                VALUES (?, ?)
            """, (key.lower(), json.dumps(data)))
        conn.commit()
    conn.close()




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
    """Fetch all persistent knowledge nodes from SQLite DB with in-memory fallback."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, category, era, lat, lng, summary_short FROM knowledge_nodes ORDER BY created_at ASC")
        rows = cursor.fetchall()
        conn.close()

        if rows:
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
    except Exception as err:
        print(f"[get_all_nodes DB Warning] {err}")

    # Fallback to in-memory fixtures for serverless cold boot
    fallback_nodes = []
    for key, data in PREBAKED_FIXTURES.items():
        title = data.get("title", key.title())
        node_id = re.sub(r'\s+', '-', title.strip().lower())
        summary = data.get("summary", "")
        summary_short = summary[:110] + "..." if len(summary) > 110 else summary
        fallback_nodes.append({
            "id": node_id,
            "title": title,
            "category": data.get("category", "History"),
            "era": data.get("era", "Historical Epoch"),
            "lat": float(data.get("coordinates", {}).get("lat", 20.0)),
            "lng": float(data.get("coordinates", {}).get("lng", 0.0)),
            "summary_short": summary_short
        })
    return fallback_nodes


# Comprehensive Pre-baked Seed Topics Fixtures
PREBAKED_FIXTURES: Dict[str, Dict[str, Any]] = {
  "mesopotamia": {
  "title": "Mesopotamia",
  "category": "History",
  "era": "4000 BCE \u2013 539 BCE",
  "wiki_query": "Mesopotamia",
  "coordinates": {
    "lat": 32.5364,
    "lng": 44.4208
  },
  "summary": "Mesopotamia, situated between the Tigris and Euphrates rivers in modern-day Iraq, is widely regarded as the Cradle of Civilization. It birthed the world's earliest cities, cuneiform writing, legal codes, and agricultural irrigation systems.",
  "milestones": [
    {
      "year": "3400 BCE",
      "event": "Sumerians develop cuneiform script, the world's first writing system."
    },
    {
      "year": "1750 BCE",
      "event": "King Hammurabi of Babylon promulgates his famous codified legal code."
    },
    {
      "year": "605 BCE",
      "event": "Construction of the Hanging Gardens of Babylon under Nebuchadnezzar II."
    }
  ],
  "trivia": "The Sumerians created a sexagesimal (base 60) numeral system, which is why modern clocks have 60 seconds in a minute and circles have 360 degrees!",
  "mindmaze_questions": [
    {
      "question": "Which two rivers bound the region known as Mesopotamia?",
      "options": [
        "Tigris and Euphrates",
        "Nile and Amazon",
        "Indus and Ganges",
        "Yellow and Yangtze"
      ],
      "correct_index": 0,
      "hint": "They flow through modern-day Iraq."
    },
    {
      "question": "What was the ancient Sumerian writing system called?",
      "options": [
        "Cuneiform",
        "Hieroglyphics",
        "Linear B",
        "Runic"
      ],
      "correct_index": 0,
      "hint": "It was written using wedge-shaped marks on clay tablets."
    },
    {
      "question": "Which Babylonian king is famous for his ancient legal code?",
      "options": [
        "Hammurabi",
        "Nebuchadnezzar",
        "Gilgamesh",
        "Sargon"
      ],
      "correct_index": 0,
      "hint": "Known for the principle of an eye for an eye."
    },
    {
      "question": "True or False: Mesopotamia is considered one of the cradles of human civilization.",
      "options": [
        "True",
        "False"
      ],
      "correct_index": 0,
      "hint": "Check the summary of this node."
    },
    {
      "question": "Which mathematical base system invented in Sumeria is still used for measuring time today?",
      "options": [
        "Base 60",
        "Base 10",
        "Base 2",
        "Base 12"
      ],
      "correct_index": 0,
      "hint": "Think about seconds in a minute."
    }
  ],
  "related_topics": [
    "Ancient Egypt",
    "Ancient Persia",
    "The Silk Road",
    "Printing Press"
  ]
},
  "mayan civilization": {
  "title": "Mayan Civilization",
  "category": "History",
  "era": "2000 BCE \u2013 1697 CE",
  "wiki_query": "Maya_civilization",
  "coordinates": {
    "lat": 20.6843,
    "lng": -88.5678
  },
  "summary": "The Maya civilization flourished across Mesoamerica, renowned for its sophisticated logo-syllabic writing system, monumental step-pyramid temples, advanced mathematics, and accurate astronomical calendars.",
  "milestones": [
    {
      "year": "750 BCE",
      "event": "Earliest monumental Mayan ceremonial architecture built at Nakbe."
    },
    {
      "year": "250 CE",
      "event": "Classic Maya golden age begins with rival city-states Tikal and Calakmul."
    },
    {
      "year": "1517 CE",
      "event": "First European contact begins the gradual Spanish conquest of the Yucatan."
    }
  ],
  "trivia": "The Maya independently developed the mathematical concept of zero centuries before it entered European mathematics!",
  "mindmaze_questions": [
    {
      "question": "Which of these Mesoamerican landmarks is famous for Maya pyramid architecture?",
      "options": [
        "Chichen Itza",
        "Machu Picchu",
        "Colosseum",
        "Parthenon"
      ],
      "correct_index": 0,
      "hint": "Located in the Yucatan Peninsula of Mexico."
    },
    {
      "question": "What mathematical concept did the Maya independently discover?",
      "options": [
        "Zero",
        "Calculus",
        "Imaginary Numbers",
        "Pi"
      ],
      "correct_index": 0,
      "hint": "It represents nothingness in place-value arithmetic."
    },
    {
      "question": "True or False: The Maya developed a sophisticated calendar based on astronomy.",
      "options": [
        "True",
        "False"
      ],
      "correct_index": 0,
      "hint": "They accurately tracked solar and lunar cycles."
    },
    {
      "question": "Which region did the Maya civilization primarily inhabit?",
      "options": [
        "Mesoamerica",
        "Andes Mountains",
        "Nile Delta",
        "Mesopotamia"
      ],
      "correct_index": 0,
      "hint": "Modern-day Mexico and Central America."
    },
    {
      "question": "Which topic is closely related to the Mayan Civilization?",
      "options": [
        "Age of Discovery",
        "Cyberpunk",
        "Silicon Valley",
        "The Beatles"
      ],
      "correct_index": 0,
      "hint": "Look for maritime exploration routes."
    }
  ],
  "related_topics": [
    "Ancient Egypt",
    "Age of Discovery",
    "Space Exploration",
    "Mesopotamia"
  ]
},
  "french revolution": {
  "title": "French Revolution",
  "category": "History",
  "era": "1789 \u2013 1799",
  "wiki_query": "French_Revolution",
  "coordinates": {
    "lat": 48.8566,
    "lng": 2.3522
  },
  "summary": "The French Revolution was a monumental political and social transformation that dismantled absolute monarchy in France, championed liberty and equality, and reshaped global modern governance.",
  "milestones": [
    {
      "year": "1789",
      "event": "Storming of the Bastille prison in Paris sparks revolutionary uprisings."
    },
    {
      "year": "1793",
      "event": "Execution of King Louis XVI and the onset of the Reign of Terror."
    },
    {
      "year": "1799",
      "event": "Napoleon Bonaparte executes a coup d'\u00e9tat, establishing the French Consulate."
    }
  ],
  "trivia": "The French Revolution introduced the metric system (meters, grams) to replace chaotic regional measurement units!",
  "mindmaze_questions": [
    {
      "question": "Which Parisian medieval fortress was stormed on July 14, 1789?",
      "options": [
        "The Bastille",
        "The Louvre",
        "Versailles",
        "Notre-Dame"
      ],
      "correct_index": 0,
      "hint": "It symbolized royal tyranny and armory."
    },
    {
      "question": "Which military leader came to power at the end of the French Revolution in 1799?",
      "options": [
        "Napoleon Bonaparte",
        "Louis XVI",
        "Robespierre",
        "Charlemagne"
      ],
      "correct_index": 0,
      "hint": "He later crowned himself Emperor of the French."
    },
    {
      "question": "What universal measurement system was introduced during the French Revolution?",
      "options": [
        "Metric System",
        "Imperial System",
        "Nautical System",
        "Roman Units"
      ],
      "correct_index": 0,
      "hint": "Based on meters and kilograms."
    },
    {
      "question": "True or False: The French Revolution overthrew the absolute monarchy in France.",
      "options": [
        "True",
        "False"
      ],
      "correct_index": 0,
      "hint": "Check the core summary of this topic."
    },
    {
      "question": "Which related topic shares historical proximity to the French Revolution?",
      "options": [
        "Industrial Revolution",
        "Quantum Computing",
        "Apollo 11",
        "The Beatles"
      ],
      "correct_index": 0,
      "hint": "Late 18th century transformation."
    }
  ],
  "related_topics": [
    "Industrial Revolution",
    "Renaissance Florence",
    "Ancient Rome",
    "Greek Philosophy"
  ]
},
  "ottoman empire": {
  "title": "Ottoman Empire",
  "category": "History",
  "era": "1299 \u2013 1922",
  "wiki_query": "Ottoman_Empire",
  "coordinates": {
    "lat": 41.0082,
    "lng": 28.9784
  },
  "summary": "Spanning Southeast Europe, Western Asia, and North Africa for over six centuries, the Ottoman Empire served as the supreme geopolitical bridge connecting Eastern and Western civilizations.",
  "milestones": [
    {
      "year": "1453",
      "event": "Sultan Mehmed II captures Constantinople, renaming it Istanbul."
    },
    {
      "year": "1520",
      "event": "Golden Age begins under Suleiman the Magnificent, expanding into Europe."
    },
    {
      "year": "1922",
      "event": "Abolition of the Ottoman Sultanate and foundation of modern Turkey."
    }
  ],
  "trivia": "Ottoman coffeehouses in 16th-century Istanbul were early social hubs where political debate and chess flourished!",
  "mindmaze_questions": [
    {
      "question": "Which historic city did Sultan Mehmed II capture in 1453?",
      "options": [
        "Constantinople",
        "Rome",
        "Athens",
        "Cairo"
      ],
      "correct_index": 0,
      "hint": "Capital of the Byzantine Empire."
    },
    {
      "question": "Under which Sultan did the Ottoman Empire reach its Golden Age in the 16th century?",
      "options": [
        "Suleiman the Magnificent",
        "Osman I",
        "Selim I",
        "Mehmed II"
      ],
      "correct_index": 0,
      "hint": "Known as Lawgiver in the East."
    },
    {
      "question": "True or False: The Ottoman Empire spanned parts of Europe, Asia, and Africa.",
      "options": [
        "True",
        "False"
      ],
      "correct_index": 0,
      "hint": "It was a major transcontinental empire."
    },
    {
      "question": "What beverage gave rise to famous social gathering houses in Istanbul?",
      "options": [
        "Coffee",
        "Tea",
        "Cocoa",
        "Cider"
      ],
      "correct_index": 0,
      "hint": "Introduced to Europe via Turkish trade."
    },
    {
      "question": "Which empire was conquered by the Ottomans in 1453?",
      "options": [
        "Byzantine Empire",
        "Roman Republic",
        "Mayan Empire",
        "Viking Empire"
      ],
      "correct_index": 0,
      "hint": "Eastern Roman Empire."
    }
  ],
  "related_topics": [
    "Byzantine Empire",
    "The Silk Road",
    "The Spice Trade",
    "Ancient Persia"
  ]
},
  "viking age": {
  "title": "Viking Age",
  "category": "History",
  "era": "793 \u2013 1066 CE",
  "wiki_query": "Viking_Age",
  "coordinates": {
    "lat": 59.9139,
    "lng": 10.7522
  },
  "summary": "The Viking Age was a period of Scandinavian maritime exploration, trade, and settlement. Norse seafarers navigated longships across Europe, the Atlantic, and into North America.",
  "milestones": [
    {
      "year": "793 CE",
      "event": "Norse raiders strike Lindisfarne monastery in northern England."
    },
    {
      "year": "1000 CE",
      "event": "Leif Erikson establishes a Norse settlement at L'Anse aux Meadows in Canada."
    },
    {
      "year": "1066 CE",
      "event": "King Harald Hardrada is defeated at Stamford Bridge, ending the Viking Age."
    }
  ],
  "trivia": "Viking longships featured double-ended symmetric hulls allowing them to reverse direction without turning around!",
  "mindmaze_questions": [
    {
      "question": "Which Norse explorer established a settlement in North America around 1000 CE?",
      "options": [
        "Leif Erikson",
        "Erik the Red",
        "Harald Hardrada",
        "Ragnar Lothbrok"
      ],
      "correct_index": 0,
      "hint": "Son of Erik the Red."
    },
    {
      "question": "What iconic vessel enabled Viking oceanic and river navigation?",
      "options": [
        "Longship",
        "Caravel",
        "Galley",
        "Trireme"
      ],
      "correct_index": 0,
      "hint": "Shallow draft wooden ship."
    },
    {
      "question": "Which monastery raid in 793 CE marks the traditional start of the Viking Age?",
      "options": [
        "Lindisfarne",
        "Iona",
        "Cluny",
        "Mont Saint-Michel"
      ],
      "correct_index": 0,
      "hint": "Located off the coast of Northumberland."
    },
    {
      "question": "True or False: Vikings navigated rivers deep into Russia and Eastern Europe.",
      "options": [
        "True",
        "False"
      ],
      "correct_index": 0,
      "hint": "They traded as far as Constantinople."
    },
    {
      "question": "Which related topic shares maritime exploration routes with the Viking Age?",
      "options": [
        "Transatlantic Voyages",
        "Silicon Valley",
        "Quantum Physics",
        "Cyberpunk"
      ],
      "correct_index": 0,
      "hint": "Crossing the Atlantic Ocean."
    }
  ],
  "related_topics": [
    "Age of Discovery",
    "Transatlantic Voyages",
    "Industrial Revolution",
    "Byzantine Empire"
  ]
},
  "mongol empire": {
  "title": "Mongol Empire",
  "category": "History",
  "era": "1206 \u2013 1368",
  "wiki_query": "Mongol_Empire",
  "coordinates": {
    "lat": 47.9188,
    "lng": 106.9176
  },
  "summary": "Founded by Genghis Khan, the Mongol Empire became the largest contiguous land empire in history. Its Pax Mongolica unified Eurasian trade routes and cultural exchange along the Silk Road.",
  "milestones": [
    {
      "year": "1206",
      "event": "Genghis Khan unifies nomadic Mongol tribes and assumes the title of Khagan."
    },
    {
      "year": "1271",
      "event": "Kublai Khan establishes the Yuan Dynasty in China."
    },
    {
      "year": "1347",
      "event": "Pax Mongolica facilitates safe travel for merchants like Marco Polo across Asia."
    }
  ],
  "trivia": "The Mongols created 'Yam', an empire-wide postal relay system where mounted messengers covered over 200 miles a day!",
  "mindmaze_questions": [
    {
      "question": "Who unified the Mongol tribes in 1206 to found the Mongol Empire?",
      "options": [
        "Genghis Khan",
        "Kublai Khan",
        "Attila the Hun",
        "Tamerlane"
      ],
      "correct_index": 0,
      "hint": "Born with the name Tem\u00fcjin."
    },
    {
      "question": "What was the famous horse-relay postal system created by the Mongols called?",
      "options": [
        "Yam",
        "Pony Express",
        "Silk Post",
        "Runner Network"
      ],
      "correct_index": 0,
      "hint": "Three-letter name for mounted couriers."
    },
    {
      "question": "True or False: The Mongol Empire was the largest contiguous land empire in history.",
      "options": [
        "True",
        "False"
      ],
      "correct_index": 0,
      "hint": "It spanned from Eastern Europe to the Pacific Ocean."
    },
    {
      "question": "Which famous Italian merchant traveled across the Mongol Empire along the Silk Road?",
      "options": [
        "Marco Polo",
        "Christopher Columbus",
        "Vasco da Gama",
        "Magellan"
      ],
      "correct_index": 0,
      "hint": "Venetian traveler who met Kublai Khan."
    },
    {
      "question": "Which major land fortification was expanded to protect China against northern invaders?",
      "options": [
        "Great Wall of China",
        "Hadrian's Wall",
        "Berlin Wall",
        "Maginot Line"
      ],
      "correct_index": 0,
      "hint": "Spans thousands of miles across China."
    }
  ],
  "related_topics": [
    "The Silk Road",
    "Great Wall of China",
    "Byzantine Empire",
    "Ancient Persia"
  ]
},
  "cryptography": {
  "title": "Cryptography & Enigma",
  "category": "Technology",
  "era": "1900 \u2013 Present",
  "wiki_query": "Cryptography",
  "coordinates": {
    "lat": 51.9977,
    "lng": -0.7407
  },
  "summary": "Cryptography is the science of secure communication. From wartime cipher machines like Enigma to Alan Turing's Bletchley Park codebreaking, it laid the foundation for computer science.",
  "milestones": [
    {
      "year": "1918",
      "event": "Arthur Scherbius patents the electro-mechanical Enigma cipher machine."
    },
    {
      "year": "1941",
      "event": "Alan Turing builds the Bombe machine at Bletchley Park to crack German naval ciphers."
    },
    {
      "year": "1977",
      "event": "Rivest, Shamir, and Adleman introduce RSA public-key encryption."
    }
  ],
  "trivia": "Alan Turing's electromechanical Bombe machine processed over 4,000 Enigma cipher combinations per minute!",
  "mindmaze_questions": [
    {
      "question": "Which British mathematician led the Enigma codebreaking efforts at Bletchley Park?",
      "options": [
        "Alan Turing",
        "Charles Babbage",
        "Isaac Newton",
        "John von Neumann"
      ],
      "correct_index": 0,
      "hint": "Father of modern computer science."
    },
    {
      "question": "What electro-mechanical rotor machine was used by Germany for military encryption in WWII?",
      "options": [
        "Enigma",
        "Lorenz",
        "Purple",
        "Hebern"
      ],
      "correct_index": 0,
      "hint": "Featured a keyboard, plugboard, and rotating rotors."
    },
    {
      "question": "What modern public-key encryption algorithm was introduced in 1977?",
      "options": [
        "RSA",
        "DES",
        "AES",
        "SHA-256"
      ],
      "correct_index": 0,
      "hint": "Named after Rivest, Shamir, and Adleman."
    },
    {
      "question": "True or False: Cryptography forms the security backbone of internet banking and e-commerce.",
      "options": [
        "True",
        "False"
      ],
      "correct_index": 0,
      "hint": "HTTPS relies on SSL/TLS encryption."
    },
    {
      "question": "Which related technology builds directly upon cryptographic principles?",
      "options": [
        "World Wide Web",
        "Steam Engine",
        "Printing Press",
        "The Beatles"
      ],
      "correct_index": 0,
      "hint": "Secure web protocols."
    }
  ],
  "related_topics": [
    "Artificial Intelligence",
    "Silicon Valley",
    "The Internet",
    "World Wide Web"
  ]
},
  "world wide web": {
  "title": "World Wide Web",
  "category": "Technology",
  "era": "1989 \u2013 Present",
  "wiki_query": "World_Wide_Web",
  "coordinates": {
    "lat": 46.233,
    "lng": 6.0557
  },
  "summary": "The World Wide Web is an information system enabling document retrieval via HTTP links over the Internet. Invented by Tim Berners-Lee at CERN, it transformed global human communication.",
  "milestones": [
    {
      "year": "1989",
      "event": "Tim Berners-Lee writes 'Information Management: A Proposal' at CERN."
    },
    {
      "year": "1991",
      "event": "The world's first website goes public at info.cern.ch."
    },
    {
      "year": "1993",
      "event": "CERN releases the World Wide Web software into the public domain."
    }
  ],
  "trivia": "The world's first web server ran on Tim Berners-Lee's NeXT computer, which had a red label reading: 'This machine is a server. DO NOT POWER IT DOWN!'",
  "mindmaze_questions": [
    {
      "question": "Who invented the World Wide Web while working at CERN in 1989?",
      "options": [
        "Tim Berners-Lee",
        "Bill Gates",
        "Steve Jobs",
        "Vint Cerf"
      ],
      "correct_index": 0,
      "hint": "British computer scientist knighted by Queen Elizabeth."
    },
    {
      "question": "What European physics laboratory was the birthplace of the World Wide Web?",
      "options": [
        "CERN",
        "DESY",
        "Fermilab",
        "Rutherford Appleton"
      ],
      "correct_index": 0,
      "hint": "Located near Geneva, Switzerland."
    },
    {
      "question": "What protocol standard defines how web browsers request web pages?",
      "options": [
        "HTTP",
        "FTP",
        "SMTP",
        "SSH"
      ],
      "correct_index": 0,
      "hint": "Hypertext Transfer Protocol."
    },
    {
      "question": "True or False: CERN released the World Wide Web software for free into the public domain.",
      "options": [
        "True",
        "False"
      ],
      "correct_index": 0,
      "hint": "This allowed global adoption without royalties."
    },
    {
      "question": "Which related pioneer digital encyclopedia debuted on CD-ROM in 1993?",
      "options": [
        "Microsoft Encarta",
        "Wikipedia",
        "Britannica Online",
        "Yahoo"
      ],
      "correct_index": 0,
      "hint": "The title of this app!"
    }
  ],
  "related_topics": [
    "The Internet",
    "Microsoft Encarta",
    "Silicon Valley",
    "Cryptography"
  ]
},
  "quantum computing": {
  "title": "Quantum Computing",
  "category": "Technology",
  "era": "1980 \u2013 Present",
  "wiki_query": "Quantum_computing",
  "coordinates": {
    "lat": 37.403,
    "lng": -122.0322
  },
  "summary": "Quantum computing harnesses quantum mechanical phenomena like superposition and entanglement to perform complex computations exponentially faster than classical supercomputers.",
  "milestones": [
    {
      "year": "1981",
      "event": "Richard Feynman proposes quantum computers to simulate physics systems."
    },
    {
      "year": "1994",
      "event": "Peter Shor formulates a quantum algorithm for fast prime factorization."
    },
    {
      "year": "2019",
      "event": "Google Sycamore quantum processor achieves experimental Quantum Supremacy."
    }
  ],
  "trivia": "Unlike classical bits that are strictly 0 or 1, quantum bits (qubits) can exist in a superposition of both states simultaneously!",
  "mindmaze_questions": [
    {
      "question": "What fundamental unit of quantum information replaces the classical bit?",
      "options": [
        "Qubit",
        "Byte",
        "Pixel",
        "Vector"
      ],
      "correct_index": 0,
      "hint": "Short for quantum bit."
    },
    {
      "question": "Which quantum phenomenon allows qubits to exist as 0 and 1 simultaneously?",
      "options": [
        "Superposition",
        "Refraction",
        "Conduction",
        "Diffraction"
      ],
      "correct_index": 0,
      "hint": "Key quantum mechanical state."
    },
    {
      "question": "Which theoretical physicist proposed quantum computing in 1981?",
      "options": [
        "Richard Feynman",
        "Albert Einstein",
        "Niels Bohr",
        "Stephen Hawking"
      ],
      "correct_index": 0,
      "hint": "Nobel laureate known for Feynman diagrams."
    },
    {
      "question": "True or False: Quantum computers operate using classical transistors.",
      "options": [
        "False",
        "True"
      ],
      "correct_index": 0,
      "hint": "They use quantum states like superconducting circuits."
    },
    {
      "question": "Which related science discipline underpins quantum computing?",
      "options": [
        "Quantum Physics",
        "Impressionism",
        "Viking Age",
        "Deep Sea Exploration"
      ],
      "correct_index": 0,
      "hint": "Study of subatomic particles."
    }
  ],
  "related_topics": [
    "Quantum Physics",
    "Silicon Valley",
    "Artificial Intelligence",
    "Cryptography"
  ]
},
  "the telegraph": {
  "title": "The Telegraph",
  "category": "Technology",
  "era": "1837 \u2013 1950s",
  "wiki_query": "Electrical_telegraph",
  "coordinates": {
    "lat": 40.7128,
    "lng": -74.006
  },
  "summary": "The electrical telegraph was the first technology to enable instant long-distance text transmission via Morse code, shrinking global communications from weeks to minutes.",
  "milestones": [
    {
      "year": "1837",
      "event": "Samuel Morse and Alfred Vail patent the electrical telegraph and Morse code."
    },
    {
      "year": "1858",
      "event": "First transatlantic telegraph cable connects Queen Victoria and President Buchanan."
    },
    {
      "year": "1861",
      "event": "First transcontinental telegraph line links the East and West Coasts of America."
    }
  ],
  "trivia": "The first public telegraph message sent by Samuel Morse in 1844 read: 'What hath God wrought!'",
  "mindmaze_questions": [
    {
      "question": "Who co-invented the commercial electrical telegraph and code of dots and dashes?",
      "options": [
        "Samuel Morse",
        "Alexander Graham Bell",
        "Thomas Edison",
        "Guglielmo Marconi"
      ],
      "correct_index": 0,
      "hint": "Morse code is named after him."
    },
    {
      "question": "What was the first transoceanic cable laid under the Atlantic in 1858 called?",
      "options": [
        "Transatlantic Cable",
        "Pacific Wire",
        "Panama Cable",
        "Eurasian Line"
      ],
      "correct_index": 0,
      "hint": "Connected Britain and North America."
    },
    {
      "question": "What first public message did Samuel Morse send in 1844?",
      "options": [
        "What hath God wrought!",
        "Hello World!",
        "Come here Watson.",
        "Mr. Watson come."
      ],
      "correct_index": 0,
      "hint": "Biblical quotation from Numbers."
    },
    {
      "question": "True or False: The telegraph drastically sped up news and stock trading.",
      "options": [
        "True",
        "False"
      ],
      "correct_index": 0,
      "hint": "It allowed instant news transmission across continents."
    },
    {
      "question": "Which revolution was accelerated by telegraph communication?",
      "options": [
        "Industrial Revolution",
        "French Revolution",
        "Viking Age",
        "Age of Discovery"
      ],
      "correct_index": 0,
      "hint": "19th century industrialization."
    }
  ],
  "related_topics": [
    "The Internet",
    "Industrial Revolution",
    "Steam Engine",
    "Silicon Valley"
  ]
},
  "dna double helix": {
  "title": "DNA Double Helix",
  "category": "Science",
  "era": "1953 \u2013 Present",
  "wiki_query": "DNA",
  "coordinates": {
    "lat": 52.2053,
    "lng": 0.1218
  },
  "summary": "The discovery of the double-helical structure of Deoxyribonucleic Acid (DNA) unlocked the molecular code of biological inheritance, revolutionizing genetics and medicine.",
  "milestones": [
    {
      "year": "1952",
      "event": "Rosalind Franklin captures 'Photo 51', revealing the X-ray diffraction signature of DNA."
    },
    {
      "year": "1953",
      "event": "James Watson and Francis Crick publish the molecular model of the DNA double helix."
    },
    {
      "year": "2003",
      "event": "Completion of the Human Genome Project sequencing 3 billion base pairs."
    }
  ],
  "trivia": "If unwound and linked end-to-end, the DNA in a single human body would stretch from Earth to the Sun and back 60 times!",
  "mindmaze_questions": [
    {
      "question": "Which female chemist captured the crucial Photo 51 X-ray image of DNA?",
      "options": [
        "Rosalind Franklin",
        "Marie Curie",
        "Ada Lovelace",
        "Dorothy Hodgkin"
      ],
      "correct_index": 0,
      "hint": "King's College London scientist."
    },
    {
      "question": "What geometry describes the twisted ladder structure of DNA?",
      "options": [
        "Double Helix",
        "Single Strand",
        "Triple Coil",
        "Tetrahedron"
      ],
      "correct_index": 0,
      "hint": "Two spiral strands intertwined."
    },
    {
      "question": "What global biological effort mapped all 3 billion human DNA base pairs in 2003?",
      "options": [
        "Human Genome Project",
        "Apollo Project",
        "Manhattan Project",
        "CERN Project"
      ],
      "correct_index": 0,
      "hint": "Sequenced the entire human genetic code."
    },
    {
      "question": "True or False: DNA stores the genetic instructions for all living organisms.",
      "options": [
        "True",
        "False"
      ],
      "correct_index": 0,
      "hint": "Blueprint of biological life."
    },
    {
      "question": "Which scientific theory provides the broader framework for genetic evolution?",
      "options": [
        "Theory of Evolution",
        "General Relativity",
        "Quantum Physics",
        "Cyberpunk"
      ],
      "correct_index": 0,
      "hint": "Charles Darwin's natural selection."
    }
  ],
  "related_topics": [
    "Theory of Evolution",
    "Discovery of Penicillin",
    "Quantum Physics",
    "Human Neuroscience"
  ]
},
  "theory of evolution": {
  "title": "Theory of Evolution",
  "category": "Science",
  "era": "1859 \u2013 Present",
  "wiki_query": "Evolution",
  "coordinates": {
    "lat": -0.9538,
    "lng": -90.9656
  },
  "summary": "Formulated by Charles Darwin, the theory of evolution by natural selection explains how biological organisms adapt and diversify over generations through genetic inheritance.",
  "milestones": [
    {
      "year": "1835",
      "event": "Charles Darwin surveys endemic finches and tortoises in the Gal\u00e1pagos Islands."
    },
    {
      "year": "1859",
      "event": "Darwin publishes 'On the Origin of Species by Means of Natural Selection'."
    },
    {
      "year": "1930s",
      "event": "The Modern Synthesis unifies Mendelian genetics with Darwinian evolution."
    }
  ],
  "trivia": "Darwin held off on publishing his evolutionary theory for over 20 years until Alfred Russel Wallace independently formulated the exact same concept!",
  "mindmaze_questions": [
    {
      "question": "Which naturalist published 'On the Origin of Species' in 1859?",
      "options": [
        "Charles Darwin",
        "Gregor Mendel",
        "Louis Pasteur",
        "Carl Linnaeus"
      ],
      "correct_index": 0,
      "hint": "Sailed aboard HMS Beagle."
    },
    {
      "question": "Which Pacific archipelago provided key biodiversity observations for Darwin?",
      "options": [
        "Gal\u00e1pagos Islands",
        "Hawaiian Islands",
        "Fiji Islands",
        "Canary Islands"
      ],
      "correct_index": 0,
      "hint": "Famous for finches and giant tortoises."
    },
    {
      "question": "What key mechanism drives evolutionary adaptation over generations?",
      "options": [
        "Natural Selection",
        "Spontaneous Generation",
        "Cell Division",
        "Photosynthesis"
      ],
      "correct_index": 0,
      "hint": "Survival of organisms best adapted to their environment."
    },
    {
      "question": "True or False: Alfred Russel Wallace independently arrived at the theory of natural selection.",
      "options": [
        "True",
        "False"
      ],
      "correct_index": 0,
      "hint": "Prompted Darwin to co-publish in 1858."
    },
    {
      "question": "Which related molecular discovery explains how genetic traits are inherited?",
      "options": [
        "DNA Double Helix",
        "Steam Engine",
        "Printing Press",
        "The Telegraph"
      ],
      "correct_index": 0,
      "hint": "Double helix molecular code."
    }
  ],
  "related_topics": [
    "DNA Double Helix",
    "Human Neuroscience",
    "Discovery of Penicillin",
    "Greek Philosophy"
  ]
},
  "james webb telescope": {
  "title": "James Webb Telescope",
  "category": "Science",
  "era": "2021 \u2013 Present",
  "wiki_query": "James_Webb_Space_Telescope",
  "coordinates": {
    "lat": 28.5721,
    "lng": -80.648
  },
  "summary": "NASA's premier space science observatory, the James Webb Space Telescope uses high-resolution infrared instruments to observe the earliest galaxies formed after the Big Bang.",
  "milestones": [
    {
      "year": "2021",
      "event": "JWST launches successfully aboard an Ariane 5 rocket from French Guiana."
    },
    {
      "year": "2022",
      "event": "First Deep Field image reveals thousands of ancient distant galaxies."
    },
    {
      "year": "2023",
      "event": "JWST detects atmospheric water vapor and carbon dioxide on distant exoplanets."
    }
  ],
  "trivia": "JWST's primary gold-coated beryllium mirror is coated in a layer of pure gold just 100 nanometers thick!",
  "mindmaze_questions": [
    {
      "question": "What spectrum of light does the James Webb Space Telescope primarily observe?",
      "options": [
        "Infrared",
        "Ultraviolet",
        "X-Ray",
        "Radio Waves"
      ],
      "correct_index": 0,
      "hint": "Allows viewing light shifted from early cosmos."
    },
    {
      "question": "What precious metal coats JWST's 18 primary hexagonal mirror segments?",
      "options": [
        "Gold",
        "Silver",
        "Platinum",
        "Titanium"
      ],
      "correct_index": 0,
      "hint": "Maximizes infrared reflectivity."
    },
    {
      "question": "At what gravitationally stable point in space does JWST orbit 1.5 million km from Earth?",
      "options": [
        "L2 Lagrange Point",
        "Low Earth Orbit",
        "Lunar Orbit",
        "Mars Trajectory"
      ],
      "correct_index": 0,
      "hint": "Second Sun-Earth Lagrange point."
    },
    {
      "question": "True or False: JWST can peer back over 13.5 billion years to observe early galaxy formation.",
      "options": [
        "True",
        "False"
      ],
      "correct_index": 0,
      "hint": "It acts as a cosmic time machine."
    },
    {
      "question": "Which earlier space mission paved the way for JWST astronomical discovery?",
      "options": [
        "Space Exploration",
        "Steam Engine",
        "Viking Age",
        "Cyberpunk"
      ],
      "correct_index": 0,
      "hint": "Sputnik, Apollo, and Hubble lineage."
    }
  ],
  "related_topics": [
    "Space Exploration",
    "Apollo 11",
    "General Relativity",
    "Quantum Physics"
  ]
},
  "hadron collider": {
  "title": "Large Hadron Collider",
  "category": "Science",
  "era": "2008 \u2013 Present",
  "wiki_query": "Large_Hadron_Collider",
  "coordinates": {
    "lat": 46.233,
    "lng": 6.0557
  },
  "summary": "The Large Hadron Collider (LHC) at CERN is the world's largest high-energy particle accelerator, built in a 27-kilometer circular tunnel beneath the Franco-Swiss border.",
  "milestones": [
    {
      "year": "2008",
      "event": "First proton beam completes a full circuit through the 27 km ring."
    },
    {
      "year": "2012",
      "event": "CERN announces the discovery of the long-sought Higgs Boson particle."
    },
    {
      "year": "2022",
      "event": "LHC Run 3 begins collecting data at record 13.6 TeV collision energies."
    }
  ],
  "trivia": "The superconducting magnets inside the LHC operate at -271.3\u00b0C (-456.3\u00b0F), making it colder than deep outer space!",
  "mindmaze_questions": [
    {
      "question": "What fundamental subatomic particle was discovered at the LHC in 2012?",
      "options": [
        "Higgs Boson",
        "Neutrino",
        "Tachyon",
        "Graviton"
      ],
      "correct_index": 0,
      "hint": "Gives mass to fundamental particles."
    },
    {
      "question": "How long is the circular underground tunnel housing the Large Hadron Collider?",
      "options": [
        "27 kilometers",
        "5 kilometers",
        "100 kilometers",
        "10 kilometers"
      ],
      "correct_index": 0,
      "hint": "Spans beneath France and Switzerland."
    },
    {
      "question": "Which research organization operates the Large Hadron Collider near Geneva?",
      "options": [
        "CERN",
        "NASA",
        "ESA",
        "MIT"
      ],
      "correct_index": 0,
      "hint": "European Organization for Nuclear Research."
    },
    {
      "question": "True or False: LHC magnets operate near absolute zero using liquid helium cooling.",
      "options": [
        "True",
        "False"
      ],
      "correct_index": 0,
      "hint": "Operating temperature is -271.3\u00b0C."
    },
    {
      "question": "Which physics subfield is directly tested by LHC particle collisions?",
      "options": [
        "Quantum Physics",
        "Impressionism",
        "The Spice Trade",
        "French Revolution"
      ],
      "correct_index": 0,
      "hint": "Study of subatomic particles and forces."
    }
  ],
  "related_topics": [
    "Quantum Physics",
    "General Relativity",
    "World Wide Web",
    "Quantum Computing"
  ]
},
  "penicillin discovery": {
  "title": "Discovery of Penicillin",
  "category": "Science",
  "era": "1928 \u2013 Present",
  "wiki_query": "Penicillin",
  "coordinates": {
    "lat": 51.5147,
    "lng": -0.1748
  },
  "summary": "The accidental discovery of penicillin by Alexander Fleming marked the beginning of modern antibiotics, saving hundreds of millions of lives from bacterial diseases.",
  "milestones": [
    {
      "year": "1928",
      "event": "Alexander Fleming discovers Penicillium mold destroying staphylococcus bacteria."
    },
    {
      "year": "1940",
      "event": "Howard Florey and Ernst Chain isolate stable penicillin for medical trials."
    },
    {
      "year": "1944",
      "event": "Mass production of penicillin supplies Allied troops on D-Day."
    }
  ],
  "trivia": "Fleming discovered penicillin when he returned from a 2-week vacation to find mold growing on an unwashed petri dish!",
  "mindmaze_questions": [
    {
      "question": "Which Scottish physician discovered penicillin in 1928?",
      "options": [
        "Alexander Fleming",
        "Louis Pasteur",
        "Edward Jenner",
        "Robert Koch"
      ],
      "correct_index": 0,
      "hint": "Nobel laureate in St. Mary's Hospital London."
    },
    {
      "question": "What type of organism produced the antibacterial substance Fleming observed?",
      "options": [
        "Mold / Fungus",
        "Virus",
        "Algae",
        "Protozoa"
      ],
      "correct_index": 0,
      "hint": "Penicillium notatum."
    },
    {
      "question": "During which global conflict was penicillin first mass-produced for wounded soldiers?",
      "options": [
        "World War II",
        "World War I",
        "American Civil War",
        "Napoleonic Wars"
      ],
      "correct_index": 0,
      "hint": "D-Day landings in 1944."
    },
    {
      "question": "True or False: Penicillin was the world's first widely effective antibiotic medicine.",
      "options": [
        "True",
        "False"
      ],
      "correct_index": 0,
      "hint": "It revolutionized modern medicine."
    },
    {
      "question": "Which related biological science unlocked genetic antibiotic synthesis?",
      "options": [
        "DNA Double Helix",
        "Quantum Physics",
        "Silicon Valley",
        "The Telegraph"
      ],
      "correct_index": 0,
      "hint": "Molecular DNA and genetics."
    }
  ],
  "related_topics": [
    "DNA Double Helix",
    "Theory of Evolution",
    "Industrial Revolution",
    "Human Neuroscience"
  ]
},
  "neuroscience": {
  "title": "Human Neuroscience",
  "category": "Science",
  "era": "1890 \u2013 Present",
  "wiki_query": "Neuroscience",
  "coordinates": {
    "lat": 40.4168,
    "lng": -3.7038
  },
  "summary": "Neuroscience explores the structure and function of the brain and nervous system. Santiago Ram\u00f3n y Cajal's neuron doctrine established that the brain is composed of individual communicating cells.",
  "milestones": [
    {
      "year": "1899",
      "event": "Santiago Ram\u00f3n y Cajal formulates the Neuron Doctrine using Golgi staining."
    },
    {
      "year": "1924",
      "event": "Hans Berger records the first human electroencephalogram (EEG) brain waves."
    },
    {
      "year": "1990s",
      "event": "Functional Magnetic Resonance Imaging (fMRI) enables real-time brain mapping."
    }
  ],
  "trivia": "The human brain contains roughly 86 billion neurons interconnected by over 100 trillion synaptic pathways!",
  "mindmaze_questions": [
    {
      "question": "Which Spanish pathologist is known as the father of modern neuroscience for the Neuron Doctrine?",
      "options": [
        "Santiago Ram\u00f3n y Cajal",
        "Camillo Golgi",
        "Sigmund Freud",
        "Ivan Pavlov"
      ],
      "correct_index": 0,
      "hint": "Nobel laureate who drew individual brain neurons."
    },
    {
      "question": "Approximately how many individual neurons are in a human brain?",
      "options": [
        "86 billion",
        "1 million",
        "500 thousand",
        "1 trillion"
      ],
      "correct_index": 0,
      "hint": "Roughly 86,000,000,000 cells."
    },
    {
      "question": "What imaging technique measures brain activity by detecting changes in blood oxygen flow?",
      "options": [
        "fMRI",
        "X-Ray",
        "Ultrasound",
        "ECG"
      ],
      "correct_index": 0,
      "hint": "Functional Magnetic Resonance Imaging."
    },
    {
      "question": "True or False: Neurons communicate with each other across chemical junction gaps called synapses.",
      "options": [
        "True",
        "False"
      ],
      "correct_index": 0,
      "hint": "Neurotransmitters cross synaptic clefts."
    },
    {
      "question": "Which computer science discipline draws inspiration from biological brain networks?",
      "options": [
        "Artificial Intelligence",
        "The Telegraph",
        "Steam Engine",
        "Printing Press"
      ],
      "correct_index": 0,
      "hint": "Artificial Neural Networks."
    }
  ],
  "related_topics": [
    "Artificial Intelligence",
    "DNA Double Helix",
    "Theory of Evolution",
    "Greek Philosophy"
  ]
},
  "greek philosophy": {
  "title": "Greek Philosophy",
  "category": "Art & Culture",
  "era": "600 BCE \u2013 300 BCE",
  "wiki_query": "Ancient_Greek_philosophy",
  "coordinates": {
    "lat": 37.9838,
    "lng": 23.7275
  },
  "summary": "Classical Greek philosophy in Athens laid the foundational framework of Western rational thought, political ethics, logic, and natural philosophy through Socrates, Plato, and Aristotle.",
  "milestones": [
    {
      "year": "399 BCE",
      "event": "Trial and execution of Socrates in democratic Athens."
    },
    {
      "year": "387 BCE",
      "event": "Plato establishes the Academy of Athens, Western Europe's first institution of higher learning."
    },
    {
      "year": "335 BCE",
      "event": "Aristotle founds the Lyceum school and formulates formal logic."
    }
  ],
  "trivia": "Plato's Academy operated in a sacred olive grove outside Athens for over 900 years!",
  "mindmaze_questions": [
    {
      "question": "Which Athenian philosopher was sentenced to drink hemlock poison in 399 BCE?",
      "options": [
        "Socrates",
        "Plato",
        "Aristotle",
        "Pythagoras"
      ],
      "correct_index": 0,
      "hint": "Teacher of Plato famous for Socratic questioning."
    },
    {
      "question": "Which academy founded by Plato in 387 BCE is considered Western Europe's first university?",
      "options": [
        "Academy of Athens",
        "Lyceum",
        "Museum of Alexandria",
        "Library of Pergamum"
      ],
      "correct_index": 0,
      "hint": "Located in an olive grove near Athens."
    },
    {
      "question": "Which philosopher tutored Alexander the Great and wrote on ethics, logic, and biology?",
      "options": [
        "Aristotle",
        "Socrates",
        "Epicurus",
        "Zeno"
      ],
      "correct_index": 0,
      "hint": "Student of Plato at the Academy."
    },
    {
      "question": "True or False: Ancient Greek philosophy laid key groundwork for scientific inquiry.",
      "options": [
        "True",
        "False"
      ],
      "correct_index": 0,
      "hint": "Emphasized empirical observation and rational logic."
    },
    {
      "question": "Which city state was the supreme intellectual heart of Classical Greek philosophy?",
      "options": [
        "Athens",
        "Sparta",
        "Troy",
        "Corinth"
      ],
      "correct_index": 0,
      "hint": "Capital of modern Greece."
    }
  ],
  "related_topics": [
    "Ancient Rome",
    "Renaissance Florence",
    "Theory of Evolution",
    "Human Neuroscience"
  ]
},
  "baroque music": {
  "title": "Baroque Music & Bach",
  "category": "Art & Culture",
  "era": "1600 \u2013 1750",
  "wiki_query": "Baroque_music",
  "coordinates": {
    "lat": 51.3397,
    "lng": 12.3731
  },
  "summary": "Baroque music brought complex counterpoint, fugal polyphony, and opera to Western classical music, defined by master composers Johann Sebastian Bach, Antonio Vivaldi, and George Frideric Handel.",
  "milestones": [
    {
      "year": "1607",
      "event": "Claudio Monteverdi premieres 'L'Orfeo', establishing early opera."
    },
    {
      "year": "1721",
      "event": "J.S. Bach completes his monumental 'Brandenburg Concertos'."
    },
    {
      "year": "1741",
      "event": "George Frideric Handel composes his choral masterpiece 'Messiah'."
    }
  ],
  "trivia": "Johann Sebastian Bach composed over 1,000 distinct musical works during his lifetime, including over 200 sacred cantatas!",
  "mindmaze_questions": [
    {
      "question": "Which German Baroque composer wrote the Brandenburg Concertos and The Well-Tempered Clavier?",
      "options": [
        "Johann Sebastian Bach",
        "Mozart",
        "Beethoven",
        "Vivaldi"
      ],
      "correct_index": 0,
      "hint": "Master of fugal counterpoint."
    },
    {
      "question": "Which Italian Baroque composer wrote the famous violin concertos known as 'The Four Seasons'?",
      "options": [
        "Antonio Vivaldi",
        "Monteverdi",
        "Puccini",
        "Scarlatti"
      ],
      "correct_index": 0,
      "hint": "Known as The Red Priest."
    },
    {
      "question": "What musical form involving interweaving melodic lines (polyphony) peaked during the Baroque era?",
      "options": [
        "Fugue",
        "Symphony",
        "Sonata",
        "Waltz"
      ],
      "correct_index": 0,
      "hint": "Contrapuntal composition technique."
    },
    {
      "question": "True or False: Opera as a theatrical musical genre originated during the Baroque era.",
      "options": [
        "True",
        "False"
      ],
      "correct_index": 0,
      "hint": "Monteverdi's L'Orfeo in 1607."
    },
    {
      "question": "Which related artistic era followed the Renaissance and built upon European patronage?",
      "options": [
        "Renaissance Florence",
        "Industrial Revolution",
        "Cyberpunk",
        "Viking Age"
      ],
      "correct_index": 0,
      "hint": "Artistic rebirth in Italy."
    }
  ],
  "related_topics": [
    "The Beatles",
    "Renaissance Florence",
    "Surrealism",
    "Printing Press"
  ]
},
  "surrealism": {
  "title": "Surrealism & Dal\u00ed",
  "category": "Art & Culture",
  "era": "1920 \u2013 1950",
  "wiki_query": "Surrealism",
  "coordinates": {
    "lat": 48.8566,
    "lng": 2.3522
  },
  "summary": "Surrealism was an avant-garde cultural movement that sought to release the uninhibited imagery of the subconscious mind. Visual artists like Salvador Dal\u00ed and Ren\u00e9 Magritte painted iconic dreamscapes.",
  "milestones": [
    {
      "year": "1924",
      "event": "Andr\u00e9 Breton publishes the Surrealist Manifesto in Paris."
    },
    {
      "year": "1931",
      "event": "Salvador Dal\u00ed paints 'The Persistence of Memory' featuring melting pocket watches."
    },
    {
      "year": "1936",
      "event": "International Surrealist Exhibition opens in London to widespread acclaim."
    }
  ],
  "trivia": "Salvador Dal\u00ed used to fall asleep holding a heavy metal key over a plate; when his hand relaxed and the key dropped, he instantly woke up to sketch his dream imagery!",
  "mindmaze_questions": [
    {
      "question": "Which Spanish painter created the famous 1931 surrealist work 'The Persistence of Memory'?",
      "options": [
        "Salvador Dal\u00ed",
        "Pablo Picasso",
        "Joan Mir\u00f3",
        "Francisco Goya"
      ],
      "correct_index": 0,
      "hint": "Famous for his iconic eccentric mustache."
    },
    {
      "question": "What objects are famously portrayed melting in Dal\u00ed's 'The Persistence of Memory'?",
      "options": [
        "Pocket Watches / Clocks",
        "Guitars",
        "Mirrors",
        "Telephones"
      ],
      "correct_index": 0,
      "hint": "Symbols of time melting away."
    },
    {
      "question": "Who published the Surrealist Manifesto in Paris in 1924?",
      "options": [
        "Andr\u00e9 Breton",
        "Max Ernst",
        "Ren\u00e9 Magritte",
        "Marcel Duchamp"
      ],
      "correct_index": 0,
      "hint": "French writer and poet."
    },
    {
      "question": "True or False: Surrealism drew heavy inspiration from Freud's psychoanalysis and dream theories.",
      "options": [
        "True",
        "False"
      ],
      "correct_index": 0,
      "hint": "Explored the unconscious mind."
    },
    {
      "question": "Which related modern visual media was influenced by surrealist trick photography?",
      "options": [
        "Cinema Pioneers",
        "Printing Press",
        "Ancient Rome",
        "The Telegraph"
      ],
      "correct_index": 0,
      "hint": "Motion pictures and special effects."
    }
  ],
  "related_topics": [
    "Impressionism",
    "Cyberpunk",
    "Cinema Pioneers",
    "Renaissance Florence"
  ]
},
  "cinema pioneers": {
  "title": "Cinema Pioneers",
  "category": "Art & Culture",
  "era": "1895 \u2013 1930",
  "wiki_query": "History_of_film",
  "coordinates": {
    "lat": 45.764,
    "lng": 4.8357
  },
  "summary": "The birth of motion pictures transformed global storytelling. Pioneers Auguste and Louis Lumi\u00e8re and illusionist Georges M\u00e9li\u00e8s invented projection technology and cinematic special effects.",
  "milestones": [
    {
      "year": "1895",
      "event": "Lumi\u00e8re brothers host the first commercial film screening in Paris."
    },
    {
      "year": "1902",
      "event": "Georges M\u00e9li\u00e8s directs sci-fi fantasy film 'A Trip to the Moon'."
    },
    {
      "year": "1927",
      "event": "Release of 'The Jazz Singer', ushering in synchronized sound 'talkies'."
    }
  ],
  "trivia": "Audience members at early Lumi\u00e8re screenings reportedly ducked in panic when watching 'Arrival of a Train at La Ciotat', fearing the train would crash through the screen!",
  "mindmaze_questions": [
    {
      "question": "Which French brothers hosted the first public projected film screening in 1895?",
      "options": [
        "Lumi\u00e8re Brothers",
        "Wright Brothers",
        "Montgolfier Brothers",
        "Warner Brothers"
      ],
      "correct_index": 0,
      "hint": "Auguste and Louis."
    },
    {
      "question": "Which 1902 silent film by Georges M\u00e9li\u00e8s featured a rocket hitting the Man in the Moon's eye?",
      "options": [
        "A Trip to the Moon",
        "Metropolis",
        "The Great Train Robbery",
        "Nosferatu"
      ],
      "correct_index": 0,
      "hint": "Early sci-fi cinema landmark."
    },
    {
      "question": "What 1927 movie marked the revolution of synchronized dialogue ('talkies')?",
      "options": [
        "The Jazz Singer",
        "Citizen Kane",
        "Singin' in the Rain",
        "Metropolis"
      ],
      "correct_index": 0,
      "hint": "Starred Al Jolson."
    },
    {
      "question": "True or False: Early films were silent and often accompanied by live organ or piano music.",
      "options": [
        "True",
        "False"
      ],
      "correct_index": 0,
      "hint": "Before sound sync technology."
    },
    {
      "question": "Which musical revolution in the 1960s was documented heavily on pop television and film?",
      "options": [
        "The Beatles",
        "Baroque Music",
        "Greek Philosophy",
        "Viking Age"
      ],
      "correct_index": 0,
      "hint": "John, Paul, George, and Ringo."
    }
  ],
  "related_topics": [
    "Surrealism",
    "The Beatles",
    "Industrial Revolution",
    "Printing Press"
  ]
},
  "transatlantic voyages": {
  "title": "Transatlantic Voyages",
  "category": "Trade & Exploration",
  "era": "1492 \u2013 1900s",
  "wiki_query": "Transatlantic_crossing",
  "coordinates": {
    "lat": 25.0343,
    "lng": -77.3963
  },
  "summary": "Oceanic transatlantic routes linked Afro-Eurasia with the Americas, sparking the Columbian Exchange of crops, culture, and trade between the Old and New Worlds.",
  "milestones": [
    {
      "year": "1492",
      "event": "Christopher Columbus lands in the Bahamas, establishing transatlantic routes."
    },
    {
      "year": "1522",
      "event": "Juan Sebasti\u00e1n Elcano completes Ferdinand Magellan's global circumnavigation."
    },
    {
      "year": "1838",
      "event": "SS Great Western provides regular transatlantic steamship passenger service."
    }
  ],
  "trivia": "The Columbian Exchange introduced potatoes, tomatoes, maize, and cocoa to Europe for the very first time!",
  "mindmaze_questions": [
    {
      "question": "In what year did Christopher Columbus cross the Atlantic to reach the Bahamas?",
      "options": [
        "1492",
        "1453",
        "1520",
        "1620"
      ],
      "correct_index": 0,
      "hint": "In fourteen hundred and ninety-two..."
    },
    {
      "question": "What exchange of crops, animals, and pathogens occurred across the Atlantic after 1492?",
      "options": [
        "Columbian Exchange",
        "Silk Road Exchange",
        "Hanseatic Trade",
        "Triangular Trade"
      ],
      "correct_index": 0,
      "hint": "Named after Columbus."
    },
    {
      "question": "Which American crop introduced to Europe revolutionized European agriculture and diet?",
      "options": [
        "Potato",
        "Wheat",
        "Barley",
        "Rice"
      ],
      "correct_index": 0,
      "hint": "Staple root crop."
    },
    {
      "question": "True or False: Transatlantic steamships in the 19th century replaced wooden sailing caravels.",
      "options": [
        "True",
        "False"
      ],
      "correct_index": 0,
      "hint": "Steam engines enabled reliable ocean schedules."
    },
    {
      "question": "Which maritime era laid the foundation for transatlantic exploration routes?",
      "options": [
        "Age of Discovery",
        "Viking Age",
        "Industrial Revolution",
        "Quantum Physics"
      ],
      "correct_index": 0,
      "hint": "Global European maritime expeditions."
    }
  ],
  "related_topics": [
    "Age of Discovery",
    "The Spice Trade",
    "Viking Age",
    "Industrial Revolution"
  ]
},
  "spice trade": {
  "title": "The Spice Trade",
  "category": "Trade & Exploration",
  "era": "1000 BCE \u2013 1700 CE",
  "wiki_query": "Spice_trade",
  "coordinates": {
    "lat": -4.5624,
    "lng": 129.9042
  },
  "summary": "The spice trade was a historical maritime network exchanging cinnamon, black pepper, and nutmeg between Asia, the Middle East, and Europe, driving global maritime exploration.",
  "milestones": [
    {
      "year": "1498",
      "event": "Vasco da Gama sails around Africa to reach the Malabar spice coast of India."
    },
    {
      "year": "1602",
      "event": "Dutch East India Company (VOC) is chartered as the world's first public corporation."
    },
    {
      "year": "1667",
      "event": "Treaty of Breda: The Dutch trade Manhattan island to Britain in exchange for the nutmeg island of Run."
    }
  ],
  "trivia": "In 16th-century Europe, a single pound of nutmeg in the Banda Islands could be sold for over 60,000% profit!",
  "mindmaze_questions": [
    {
      "question": "Which Portuguese explorer reached the Malabar spice coast of India in 1498 by sailing around Africa?",
      "options": [
        "Vasco da Gama",
        "Columbus",
        "Magellan",
        "Marco Polo"
      ],
      "correct_index": 0,
      "hint": "Navigated around the Cape of Good Hope."
    },
    {
      "question": "Which island did the Dutch trade to the British in 1667 in exchange for the nutmeg island of Run?",
      "options": [
        "Manhattan",
        "Jamaica",
        "Madagascar",
        "Ceylon"
      ],
      "correct_index": 0,
      "hint": "Now the central borough of New York City."
    },
    {
      "question": "What was the world's first publicly traded corporation, founded by the Dutch for spice commerce in 1602?",
      "options": [
        "Dutch East India Company (VOC)",
        "British East India Company",
        "Hudson's Bay Company",
        "Muscovy Company"
      ],
      "correct_index": 0,
      "hint": "Known by initials VOC."
    },
    {
      "question": "True or False: Spices like pepper and nutmeg were used for medicinal and culinary preservation purposes.",
      "options": [
        "True",
        "False"
      ],
      "correct_index": 0,
      "hint": "Spices were highly prized commodities."
    },
    {
      "question": "Which ancient trade network connected spice routes over land across Asia?",
      "options": [
        "The Silk Road",
        "Transatlantic Voyages",
        "Apollo 11",
        "Silicon Valley"
      ],
      "correct_index": 0,
      "hint": "Transcontinental Asian trade road."
    }
  ],
  "related_topics": [
    "The Silk Road",
    "Age of Discovery",
    "Transatlantic Voyages",
    "Ottoman Empire"
  ]
},
  "antarctic expeditions": {
  "title": "Antarctic Expeditions",
  "category": "Trade & Exploration",
  "era": "1820 \u2013 Present",
  "wiki_query": "Heroic_Age_of_Antarctic_Exploration",
  "coordinates": {
    "lat": -75.2509,
    "lng": -0.0713
  },
  "summary": "Polar exploration of Earth's southernmost continent saw explorers brave extreme freezing environments, culminating in Roald Amundsen reaching the South Pole in 1911.",
  "milestones": [
    {
      "year": "1820",
      "event": "Fabian Gottlieb von Bellingshausen sights the Antarctic ice shelf."
    },
    {
      "year": "1911",
      "event": "Roald Amundsen leads the first expedition to reach the geographic South Pole."
    },
    {
      "year": "1959",
      "event": "Twelve nations sign the Antarctic Treaty reserving the continent for peaceful scientific research."
    }
  ],
  "trivia": "Antarctica contains 70% of the world's fresh water and 90% of Earth's ice, yet receives so little precipitation it is technically classified as a desert!",
  "mindmaze_questions": [
    {
      "question": "Which Norwegian polar explorer led the first team to reach the South Pole in December 1911?",
      "options": [
        "Roald Amundsen",
        "Robert Falcon Scott",
        "Ernest Shackleton",
        "Fridtjof Nansen"
      ],
      "correct_index": 0,
      "hint": "Beat Scott's British expedition by one month."
    },
    {
      "question": "What 1959 international agreement demilitarized Antarctica and designated it for scientific study?",
      "options": [
        "Antarctic Treaty",
        "Geneva Convention",
        "Paris Agreement",
        "Kyoto Protocol"
      ],
      "correct_index": 0,
      "hint": "Signed by 12 founding nations."
    },
    {
      "question": "True or False: Antarctica is technically classified as a desert due to low annual precipitation.",
      "options": [
        "True",
        "False"
      ],
      "correct_index": 0,
      "hint": "It receives very little rain or snowfall."
    },
    {
      "question": "What percentage of Earth's fresh water is frozen in the Antarctic ice sheet?",
      "options": [
        "70%",
        "30%",
        "50%",
        "95%"
      ],
      "correct_index": 0,
      "hint": "The majority of global fresh water."
    },
    {
      "question": "Which related extreme environment exploration pushes technology to its limits?",
      "options": [
        "Deep Sea Exploration",
        "The Spice Trade",
        "Printing Press",
        "Renaissance Florence"
      ],
      "correct_index": 0,
      "hint": "Submersible deep trench diving."
    }
  ],
  "related_topics": [
    "Deep Sea Exploration",
    "Age of Discovery",
    "Space Exploration",
    "Transatlantic Voyages"
  ]
},
  "deep sea exploration": {
  "title": "Deep Sea Exploration",
  "category": "Trade & Exploration",
  "era": "1960 \u2013 Present",
  "wiki_query": "Deep-sea_exploration",
  "coordinates": {
    "lat": 11.3493,
    "lng": 142.1996
  },
  "summary": "Deep sea exploration uses pressurized submersibles to investigate Earth's deepest abyssal trenches and hydrothermal vents, discovering extreme lifeforms near volcanic ocean ridges.",
  "milestones": [
    {
      "year": "1960",
      "event": "Jacques Piccard and Don Walsh descend to Challenger Deep in bathyscaphe Trieste."
    },
    {
      "year": "1977",
      "event": "Discovery of chemosynthetic hydrothermal vent ecosystems at the Galapagos Rift."
    },
    {
      "year": "1985",
      "event": "Robert Ballard locates the deep ocean wreck of RMS Titanic."
    }
  ],
  "trivia": "At the bottom of the Mariana Trench (Challenger Deep), water pressure exceeds 1,000 atmospheres\u2014equivalent to an elephant standing on your thumb!",
  "mindmaze_questions": [
    {
      "question": "What is the deepest known point in Earth's oceans, located in the Mariana Trench?",
      "options": [
        "Challenger Deep",
        "Puerto Rico Trench",
        "Java Trench",
        "Sunda Deep"
      ],
      "correct_index": 0,
      "hint": "Reached by bathyscaphe Trieste in 1960."
    },
    {
      "question": "Which deep ocean shipwreck was discovered by Robert Ballard in 1985 using ARGO submersible cameras?",
      "options": [
        "RMS Titanic",
        "Bismarck",
        "Lusitania",
        "Endurance"
      ],
      "correct_index": 0,
      "hint": "Sank in 1912 after striking an iceberg."
    },
    {
      "question": "What energy source powers chemosynthetic ecosystems around deep hydrothermal vents?",
      "options": [
        "Chemical compounds / Sulfur",
        "Sunlight",
        "Photosynthesis",
        "Nuclear Energy"
      ],
      "correct_index": 0,
      "hint": "Volcanic minerals dissolved in superheated water."
    },
    {
      "question": "True or False: The pressure at the bottom of Challenger Deep is over 1,000 times atmospheric pressure.",
      "options": [
        "True",
        "False"
      ],
      "correct_index": 0,
      "hint": "Over 8 tons per square inch."
    },
    {
      "question": "Which related polar exploration field shares remote environmental monitoring techniques?",
      "options": [
        "Antarctic Expeditions",
        "Greek Philosophy",
        "Gutenberg Bible",
        "The Beatles"
      ],
      "correct_index": 0,
      "hint": "Polar South Pole expeditions."
    }
  ],
  "related_topics": [
    "Antarctic Expeditions",
    "Space Exploration",
    "The Spice Trade",
    "Industrial Revolution"
  ]
},
'microsoft encarta': {'title': 'Microsoft Encarta',
                       'category': 'Technology',
                       'era': '1993 – 2009',
                       'wiki_query': 'Encarta',
                       'coordinates': {'lat': 47.6405, 'lng': -122.1297},
                       'summary': 'Microsoft Encarta was a digital multimedia encyclopedia published by Microsoft from '
                                  '1993 to 2009. Originally released on CD-ROM with interactive 3D globes, sound '
                                  'clips, and MindMaze trivia games, Encarta revolutionized digital education and '
                                  'knowledge exploration for millions of users worldwide.',
                       'milestones': [{'year': '1993',
                                       'event': 'Microsoft launches Encarta on CD-ROM based on Funk & Wagnalls '
                                                'encyclopedia.'},
                                      {'year': '1995',
                                       'event': 'Encarta 95 debuts MindMaze 2D trivia dungeon game and audio sound '
                                                'clips.'},
                                      {'year': '2000',
                                       'event': 'Encarta Africana and online web encyclopedia search integration '
                                                'introduced.'},
                                      {'year': '2009',
                                       'event': 'Microsoft discontinues Encarta CD-ROM disc production as Web 2.0 '
                                                'expands.'},
                                      {'year': '2026',
                                       'event': 'Encarta 2.0 (NewGen Retro Edition) is reborn with 3D WebGL spatial '
                                                'nodes!'}],
                       'trivia': "Encarta's iconic MindMaze game was designed to make encyclopedia research addictive "
                                 'by locking castle doors behind historical multiple-choice trivia challenges!',
                       'mindmaze_questions': [{'question': 'In what year did Microsoft release the very first edition '
                                                           'of Encarta on CD-ROM?',
                                               'options': ['1993', '1995', '1998', '2001'],
                                               'correct_index': 0,
                                               'hint': 'It was launched in the early 90s based on Funk & Wagnalls '
                                                       'content.'},
                                              {'question': 'What famous 2D trivia dungeon maze game was built directly '
                                                           'into classic Encarta?',
                                               'options': ['MindMaze',
                                                           'Math Blaster',
                                                           'Where in the World is Carmen Sandiego?',
                                                           'Oregon Trail'],
                                               'correct_index': 0,
                                               'hint': 'Players guided a knight through castle doors by answering '
                                                       'encyclopedia trivia.'},
                                              {'question': 'True or False: Microsoft Encarta is primarily categorized '
                                                           'under Technology?',
                                               'options': ['True', 'False'],
                                               'correct_index': 0,
                                               'hint': 'Check the main category of this node.'},
                                              {'question': 'Which of these eras is most closely associated with '
                                                           'Microsoft Encarta?',
                                               'options': ['1993 – 2009', '2099 - Present', '10,000 BCE', 'Unknown'],
                                               'correct_index': 0,
                                               'hint': 'Think about the timeline of this topic.'},
                                              {'question': 'Which of the following is considered a related topic to '
                                                           'Microsoft Encarta?',
                                               'options': ['Silicon Valley',
                                                           'Alien Abductions',
                                                           'Baking Bread',
                                                           'The Matrix'],
                                               'correct_index': 0,
                                               'hint': 'Look for the most logically connected topic.'}],
                       'related_topics': ['Silicon Valley', 'Ancient Rome', 'Quantum Physics', 'Renaissance Florence']},
 'the silk road': {'title': 'The Silk Road',
                   'category': 'Trade & Exploration',
                   'era': '130 BCE – 1453 CE',
                   'wiki_query': 'Silk_Road',
                   'coordinates': {'lat': 34.3416, 'lng': 108.9398},
                   'summary': 'The Silk Road was a network of Eurasian trade routes active from the second century BCE '
                              'until the mid-15th century. Spanning over 6,400 kilometers, it played a central role in '
                              'facilitating economic, cultural, political, and religious interactions between the East '
                              'and West.',
                   'milestones': [{'year': '130 BCE',
                                   'event': 'Han Dynasty officially opens trade routes with the West.'},
                                  {'year': '1271 CE',
                                   'event': 'Marco Polo embarks on his journey along the Silk Road.'},
                                  {'year': '1453 CE',
                                   'event': 'Ottoman Empire boycotts trade with the West, leading to the decline of '
                                            'the overland Silk Road.'}],
                   'trivia': 'The Silk Road was named in the 19th century by German geographer Ferdinand von '
                             'Richthofen, though the ancient network traded far more than just silk!',
                   'mindmaze_questions': [{'question': "Which empire's boycott of Western trade in 1453 led to the "
                                                       'decline of the overland Silk Road?',
                                           'options': ['Ottoman Empire',
                                                       'Roman Empire',
                                                       'Mongol Empire',
                                                       'Byzantine Empire'],
                                           'correct_index': 0,
                                           'hint': 'Their capture of Constantinople effectively blocked European '
                                                   'access.'},
                                          {'question': 'True or False: The Silk Road is primarily categorized under '
                                                       'Trade & Exploration?',
                                           'options': ['True', 'False'],
                                           'correct_index': 0,
                                           'hint': 'Check the main category of this node.'},
                                          {'question': 'Which of these eras is most closely associated with The Silk '
                                                       'Road?',
                                           'options': ['130 BCE – 1453 CE', '2099 - Present', '10,000 BCE', 'Unknown'],
                                           'correct_index': 0,
                                           'hint': 'Think about the timeline of this topic.'},
                                          {'question': 'Which of the following is considered a related topic to The '
                                                       'Silk Road?',
                                           'options': ['Byzantine Empire',
                                                       'Alien Abductions',
                                                       'Baking Bread',
                                                       'The Matrix'],
                                           'correct_index': 0,
                                           'hint': 'Look for the most logically connected topic.'},
                                          {'question': 'Did The Silk Road have a profound impact on human knowledge?',
                                           'options': ['Yes, absolutely',
                                                       'No, not really',
                                                       'Only mildly',
                                                       'It was completely forgotten'],
                                           'correct_index': 0,
                                           'hint': "It's in this encyclopedia for a reason!"}],
                   'related_topics': ['Byzantine Empire', 'Ancient Persia', 'Age of Discovery']},
 'byzantine empire': {'title': 'Byzantine Empire',
                      'category': 'History',
                      'era': '330 CE – 1453 CE',
                      'wiki_query': 'Byzantine_Empire',
                      'coordinates': {'lat': 41.0082, 'lng': 28.9784},
                      'summary': 'The Byzantine Empire, also referred to as the Eastern Roman Empire, was the '
                                 'continuation of the Roman Empire primarily in its eastern provinces during Late '
                                 'Antiquity and the Middle Ages. Its capital city was Constantinople.',
                      'milestones': [{'year': '330 CE',
                                      'event': 'Constantine the Great dedicates Constantinople as the new capital.'},
                                     {'year': '537 CE',
                                      'event': 'Hagia Sophia is completed under Emperor Justinian I.'},
                                     {'year': '1453 CE', 'event': 'Fall of Constantinople to the Ottoman Empire.'}],
                      'trivia': 'The Byzantine Empire preserved ancient Greek and Roman literature, acting as a '
                                'crucial bridge to the Renaissance!',
                      'mindmaze_questions': [{'question': 'What was the capital city of the Byzantine Empire?',
                                              'options': ['Constantinople', 'Rome', 'Athens', 'Alexandria'],
                                              'correct_index': 0,
                                              'hint': 'It was named after Emperor Constantine.'},
                                             {'question': 'True or False: Byzantine Empire is primarily categorized '
                                                          'under History?',
                                              'options': ['True', 'False'],
                                              'correct_index': 0,
                                              'hint': 'Check the main category of this node.'},
                                             {'question': 'Which of these eras is most closely associated with '
                                                          'Byzantine Empire?',
                                              'options': ['330 CE – 1453 CE',
                                                          '2099 - Present',
                                                          '10,000 BCE',
                                                          'Unknown'],
                                              'correct_index': 0,
                                              'hint': 'Think about the timeline of this topic.'},
                                             {'question': 'Which of the following is considered a related topic to '
                                                          'Byzantine Empire?',
                                              'options': ['Ancient Rome',
                                                          'Alien Abductions',
                                                          'Baking Bread',
                                                          'The Matrix'],
                                              'correct_index': 0,
                                              'hint': 'Look for the most logically connected topic.'},
                                             {'question': 'Did Byzantine Empire have a profound impact on human '
                                                          'knowledge?',
                                              'options': ['Yes, absolutely',
                                                          'No, not really',
                                                          'Only mildly',
                                                          'It was completely forgotten'],
                                              'correct_index': 0,
                                              'hint': "It's in this encyclopedia for a reason!"}],
                      'related_topics': ['Ancient Rome', 'The Silk Road', 'Renaissance Florence']},
 'ancient rome': {'title': 'Ancient Rome',
                  'category': 'History',
                  'era': '753 BCE – 476 CE',
                  'wiki_query': 'Ancient_Rome',
                  'coordinates': {'lat': 41.9028, 'lng': 12.4964},
                  'summary': 'Ancient Rome evolved from an iron-age agrarian settlement on the Italian Peninsula into '
                             'one of the largest empires in world history. Famous for its military organization, '
                             'monumental architecture like the Colosseum, and complex legal systems.',
                  'milestones': [{'year': '753 BCE', 'event': 'Legendary founding of Rome by Romulus and Remus.'},
                                 {'year': '44 BCE', 'event': 'Assassination of Julius Caesar.'},
                                 {'year': '476 CE', 'event': 'Fall of the Western Roman Empire.'}],
                  'trivia': 'The Romans used volcanic ash and seawater to create a special concrete (pozzolana) that '
                            'hardens underwater and lasts for millennia!',
                  'mindmaze_questions': [{'question': 'According to myth, which twin brothers founded Ancient Rome?',
                                          'options': ['Romulus and Remus',
                                                      'Castor and Pollux',
                                                      'Apollo and Artemis',
                                                      'Cain and Abel'],
                                          'correct_index': 0,
                                          'hint': 'They were supposedly raised by a she-wolf.'},
                                         {'question': 'True or False: Ancient Rome is primarily categorized under '
                                                      'History?',
                                          'options': ['True', 'False'],
                                          'correct_index': 0,
                                          'hint': 'Check the main category of this node.'},
                                         {'question': 'Which of these eras is most closely associated with Ancient '
                                                      'Rome?',
                                          'options': ['753 BCE – 476 CE', '2099 - Present', '10,000 BCE', 'Unknown'],
                                          'correct_index': 0,
                                          'hint': 'Think about the timeline of this topic.'},
                                         {'question': 'Which of the following is considered a related topic to Ancient '
                                                      'Rome?',
                                          'options': ['Byzantine Empire',
                                                      'Alien Abductions',
                                                      'Baking Bread',
                                                      'The Matrix'],
                                          'correct_index': 0,
                                          'hint': 'Look for the most logically connected topic.'},
                                         {'question': 'Did Ancient Rome have a profound impact on human knowledge?',
                                          'options': ['Yes, absolutely',
                                                      'No, not really',
                                                      'Only mildly',
                                                      'It was completely forgotten'],
                                          'correct_index': 0,
                                          'hint': "It's in this encyclopedia for a reason!"}],
                  'related_topics': ['Byzantine Empire', 'Ancient Egypt', 'Renaissance Florence']},
 'ancient persia': {'title': 'Ancient Persia',
                    'category': 'History',
                    'era': '550 BCE – 330 BCE',
                    'wiki_query': 'Achaemenid_Empire',
                    'coordinates': {'lat': 29.9344, 'lng': 52.8911},
                    'summary': 'The Achaemenid Empire, also known as the First Persian Empire, was an ancient Iranian '
                               'empire founded by Cyrus the Great. At its peak, it was the largest empire the world '
                               'had ever seen, spanning from the Balkans to the Indus Valley.',
                    'milestones': [{'year': '550 BCE',
                                    'event': 'Cyrus the Great conquers the Median, Lydian, and Neo-Babylonian '
                                             'empires.'},
                                   {'year': '480 BCE',
                                    'event': 'Xerxes I invades Greece, leading to the battles of Thermopylae and '
                                             'Salamis.'},
                                   {'year': '330 BCE', 'event': 'Alexander the Great conquers the Achaemenid Empire.'}],
                    'trivia': 'The ancient Persians built a massive network of paved roads, including the Royal Road, '
                              'spanning over 1,500 miles to ensure rapid communication!',
                    'mindmaze_questions': [{'question': 'Who founded the First Persian (Achaemenid) Empire?',
                                            'options': ['Cyrus the Great',
                                                        'Darius the Great',
                                                        'Xerxes I',
                                                        'Alexander the Great'],
                                            'correct_index': 0,
                                            'hint': 'He is often credited with issuing the first charter of human '
                                                    'rights.'},
                                           {'question': 'True or False: Ancient Persia is primarily categorized under '
                                                        'History?',
                                            'options': ['True', 'False'],
                                            'correct_index': 0,
                                            'hint': 'Check the main category of this node.'},
                                           {'question': 'Which of these eras is most closely associated with Ancient '
                                                        'Persia?',
                                            'options': ['550 BCE – 330 BCE', '2099 - Present', '10,000 BCE', 'Unknown'],
                                            'correct_index': 0,
                                            'hint': 'Think about the timeline of this topic.'},
                                           {'question': 'Which of the following is considered a related topic to '
                                                        'Ancient Persia?',
                                            'options': ['Ancient Rome',
                                                        'Alien Abductions',
                                                        'Baking Bread',
                                                        'The Matrix'],
                                            'correct_index': 0,
                                            'hint': 'Look for the most logically connected topic.'},
                                           {'question': 'Did Ancient Persia have a profound impact on human knowledge?',
                                            'options': ['Yes, absolutely',
                                                        'No, not really',
                                                        'Only mildly',
                                                        'It was completely forgotten'],
                                            'correct_index': 0,
                                            'hint': "It's in this encyclopedia for a reason!"}],
                    'related_topics': ['Ancient Rome', 'The Silk Road', 'Ancient Egypt']},
 'age of discovery': {'title': 'Age of Discovery',
                      'category': 'Trade & Exploration',
                      'era': '1400 – 1600',
                      'wiki_query': 'Age_of_Discovery',
                      'coordinates': {'lat': 38.7223, 'lng': -9.1393},
                      'summary': 'The Age of Discovery was a period of extensive overseas exploration driven by '
                                 'European powers seeking new trade routes to Asia. This era established global '
                                 'maritime networks, leading to early globalization and colonization.',
                      'milestones': [{'year': '1492',
                                      'event': 'Christopher Columbus crosses the Atlantic Ocean, encountering the '
                                               'Americas.'},
                                     {'year': '1498',
                                      'event': 'Vasco da Gama reaches India by sea, opening the Cape Route.'},
                                     {'year': '1522',
                                      'event': 'Magellan-Elcano expedition completes the first circumnavigation of the '
                                               'Earth.'}],
                      'trivia': 'Scurvy, a disease caused by vitamin C deficiency, killed more sailors during the Age '
                                'of Discovery than storms, shipwrecks, and combat combined!',
                      'mindmaze_questions': [{'question': 'Which expedition completed the first successful '
                                                          'circumnavigation of the globe?',
                                              'options': ['Magellan-Elcano', 'Columbus', 'Vasco da Gama', 'James Cook'],
                                              'correct_index': 0,
                                              'hint': 'The lead explorer died in the Philippines before the journey '
                                                      'was completed.'},
                                             {'question': 'True or False: Age of Discovery is primarily categorized '
                                                          'under Trade & Exploration?',
                                              'options': ['True', 'False'],
                                              'correct_index': 0,
                                              'hint': 'Check the main category of this node.'},
                                             {'question': 'Which of these eras is most closely associated with Age of '
                                                          'Discovery?',
                                              'options': ['1400 – 1600', '2099 - Present', '10,000 BCE', 'Unknown'],
                                              'correct_index': 0,
                                              'hint': 'Think about the timeline of this topic.'},
                                             {'question': 'Which of the following is considered a related topic to Age '
                                                          'of Discovery?',
                                              'options': ['The Silk Road',
                                                          'Alien Abductions',
                                                          'Baking Bread',
                                                          'The Matrix'],
                                              'correct_index': 0,
                                              'hint': 'Look for the most logically connected topic.'},
                                             {'question': 'Did Age of Discovery have a profound impact on human '
                                                          'knowledge?',
                                              'options': ['Yes, absolutely',
                                                          'No, not really',
                                                          'Only mildly',
                                                          'It was completely forgotten'],
                                              'correct_index': 0,
                                              'hint': "It's in this encyclopedia for a reason!"}],
                      'related_topics': ['The Silk Road', 'Renaissance Florence', 'Industrial Revolution']},
 'renaissance florence': {'title': 'Renaissance Florence',
                          'category': 'Art & Culture',
                          'era': '1300 – 1600',
                          'wiki_query': 'Florence',
                          'coordinates': {'lat': 43.7696, 'lng': 11.2558},
                          'summary': 'Florence is widely regarded as the birthplace of the Renaissance, a fervent '
                                     'period of European cultural, artistic, political and economic rebirth following '
                                     'the Middle Ages. The powerful Medici family funded masters like Leonardo da '
                                     'Vinci and Michelangelo.',
                          'milestones': [{'year': '1436',
                                          'event': 'Brunelleschi finishes the dome of the Florence Cathedral.'},
                                         {'year': '1504', 'event': 'Michelangelo unveils the statue of David.'},
                                         {'year': '1513', 'event': "Machiavelli writes 'The Prince'."}],
                          'trivia': "Leonardo da Vinci often wrote his personal notes backwards, in 'mirror writing', "
                                    'to prevent others from easily stealing his ideas!',
                          'mindmaze_questions': [{'question': 'Which powerful banking family was the primary patron of '
                                                              'the arts during the Florentine Renaissance?',
                                                  'options': ['Medici', 'Borgia', 'Sforza', 'Tudor'],
                                                  'correct_index': 0,
                                                  'hint': 'They virtually ruled Florence for much of the Renaissance '
                                                          'period.'},
                                                 {'question': 'True or False: Renaissance Florence is primarily '
                                                              'categorized under Art & Culture?',
                                                  'options': ['True', 'False'],
                                                  'correct_index': 0,
                                                  'hint': 'Check the main category of this node.'},
                                                 {'question': 'Which of these eras is most closely associated with '
                                                              'Renaissance Florence?',
                                                  'options': ['1300 – 1600', '2099 - Present', '10,000 BCE', 'Unknown'],
                                                  'correct_index': 0,
                                                  'hint': 'Think about the timeline of this topic.'},
                                                 {'question': 'Which of the following is considered a related topic to '
                                                              'Renaissance Florence?',
                                                  'options': ['Ancient Rome',
                                                              'Alien Abductions',
                                                              'Baking Bread',
                                                              'The Matrix'],
                                                  'correct_index': 0,
                                                  'hint': 'Look for the most logically connected topic.'},
                                                 {'question': 'Did Renaissance Florence have a profound impact on '
                                                              'human knowledge?',
                                                  'options': ['Yes, absolutely',
                                                              'No, not really',
                                                              'Only mildly',
                                                              'It was completely forgotten'],
                                                  'correct_index': 0,
                                                  'hint': "It's in this encyclopedia for a reason!"}],
                          'related_topics': ['Ancient Rome', 'Byzantine Empire', 'Age of Discovery']},
 'industrial revolution': {'title': 'Industrial Revolution',
                           'category': 'Technology',
                           'era': '1760 – 1840',
                           'wiki_query': 'Industrial_Revolution',
                           'coordinates': {'lat': 53.4808, 'lng': -2.2426},
                           'summary': 'The Industrial Revolution marked the transition from agrarian, handicraft '
                                      'economies to machine-driven industrial manufacturing. Originating in Great '
                                      'Britain with steam power, textile mechanization, and iron metallurgy, it '
                                      'transformed urban transport and global trade.',
                           'milestones': [{'year': '1765',
                                           'event': 'James Watt invents the separate condenser steam engine.'},
                                          {'year': '1804',
                                           'event': "Trevithick builds the world's first working steam locomotive."}],
                           'trivia': "The word 'sabotage' is rumored to come from French weavers throwing wooden shoes "
                                     "('sabots') into mechanized looms!",
                           'mindmaze_questions': [{'question': 'Which inventor dramatically improved the steam engine '
                                                               'with a separate condenser in 1765?',
                                                   'options': ['James Watt',
                                                               'Thomas Newcomen',
                                                               'George Stephenson',
                                                               'Eli Whitney'],
                                                   'correct_index': 0,
                                                   'hint': 'The SI unit of power is named after him.'},
                                                  {'question': 'True or False: Industrial Revolution is primarily '
                                                               'categorized under Technology?',
                                                   'options': ['True', 'False'],
                                                   'correct_index': 0,
                                                   'hint': 'Check the main category of this node.'},
                                                  {'question': 'Which of these eras is most closely associated with '
                                                               'Industrial Revolution?',
                                                   'options': ['1760 – 1840',
                                                               '2099 - Present',
                                                               '10,000 BCE',
                                                               'Unknown'],
                                                   'correct_index': 0,
                                                   'hint': 'Think about the timeline of this topic.'},
                                                  {'question': 'Which of the following is considered a related topic '
                                                               'to Industrial Revolution?',
                                                   'options': ['Silicon Valley',
                                                               'Alien Abductions',
                                                               'Baking Bread',
                                                               'The Matrix'],
                                                   'correct_index': 0,
                                                   'hint': 'Look for the most logically connected topic.'},
                                                  {'question': 'Did Industrial Revolution have a profound impact on '
                                                               'human knowledge?',
                                                   'options': ['Yes, absolutely',
                                                               'No, not really',
                                                               'Only mildly',
                                                               'It was completely forgotten'],
                                                   'correct_index': 0,
                                                   'hint': "It's in this encyclopedia for a reason!"}],
                           'related_topics': ['Silicon Valley', 'Age of Discovery', 'Space Exploration']},
 'ancient egypt': {'title': 'Ancient Egypt',
                   'category': 'History',
                   'era': '3100 BCE – 30 BCE',
                   'wiki_query': 'Ancient_Egypt',
                   'coordinates': {'lat': 29.9792, 'lng': 31.1342},
                   'summary': 'Ancient Egypt was a civilization of ancient North Africa along the lower reaches of the '
                              'Nile River. Famous for the Great Pyramids of Giza, hieroglyphic writing, papyrus, and '
                              'monumental pharaonic architecture.',
                   'milestones': [{'year': '3100 BCE',
                                   'event': 'Unification of Upper and Lower Egypt under King Menes.'},
                                  {'year': '2560 BCE',
                                   'event': 'Completion of the Great Pyramid of Giza under Pharaoh Khufu.'},
                                  {'year': '1323 BCE',
                                   'event': 'Burial of Pharaoh Tutankhamun in the Valley of the Kings.'}],
                   'trivia': 'The Great Pyramid of Giza was the tallest man-made structure in the world for over 3,800 '
                             'years!',
                   'mindmaze_questions': [{'question': 'Which river sustained ancient Egyptian civilization?',
                                           'options': ['Nile River', 'Amazon River', 'Tigris River', 'Euphrates River'],
                                           'correct_index': 0,
                                           'hint': 'It flows northwards through Africa into the Mediterranean Sea.'},
                                          {'question': 'True or False: Ancient Egypt is primarily categorized under '
                                                       'History?',
                                           'options': ['True', 'False'],
                                           'correct_index': 0,
                                           'hint': 'Check the main category of this node.'},
                                          {'question': 'Which of these eras is most closely associated with Ancient '
                                                       'Egypt?',
                                           'options': ['3100 BCE – 30 BCE', '2099 - Present', '10,000 BCE', 'Unknown'],
                                           'correct_index': 0,
                                           'hint': 'Think about the timeline of this topic.'},
                                          {'question': 'Which of the following is considered a related topic to '
                                                       'Ancient Egypt?',
                                           'options': ['Ancient Persia',
                                                       'Alien Abductions',
                                                       'Baking Bread',
                                                       'The Matrix'],
                                           'correct_index': 0,
                                           'hint': 'Look for the most logically connected topic.'},
                                          {'question': 'Did Ancient Egypt have a profound impact on human knowledge?',
                                           'options': ['Yes, absolutely',
                                                       'No, not really',
                                                       'Only mildly',
                                                       'It was completely forgotten'],
                                           'correct_index': 0,
                                           'hint': "It's in this encyclopedia for a reason!"}],
                   'related_topics': ['Ancient Persia', 'Ancient Rome', 'The Silk Road']},
 'space exploration': {'title': 'Space Exploration',
                       'category': 'Science',
                       'era': '1957 – Present',
                       'wiki_query': 'Space_exploration',
                       'coordinates': {'lat': 28.5721, 'lng': -80.648},
                       'summary': 'Space Exploration is the discovery and exploration of celestial structures in outer '
                                  'space by means of evolving space technology. From Sputnik and the Apollo Moon '
                                  'landings to Mars rovers and the James Webb Space Telescope.',
                       'milestones': [{'year': '1957',
                                       'event': 'Soviet Union launches Sputnik 1, the first artificial Earth '
                                                'satellite.'},
                                      {'year': '1969',
                                       'event': 'Apollo 11 lands Neil Armstrong and Buzz Aldrin on the Moon.'},
                                      {'year': '2021',
                                       'event': 'James Webb Space Telescope launches to uncover early universe '
                                                'galaxies.'}],
                       'trivia': 'Footprints left on the Moon by Apollo astronauts will remain intact for millions of '
                                 'years because there is no wind or water erosion!',
                       'mindmaze_questions': [{'question': 'In what year did the Apollo 11 mission successfully land '
                                                           'humans on the Moon?',
                                               'options': ['1969', '1957', '1975', '1981'],
                                               'correct_index': 0,
                                               'hint': 'One small step for man, one giant leap for mankind.'},
                                              {'question': 'True or False: Space Exploration is primarily categorized '
                                                           'under Science?',
                                               'options': ['True', 'False'],
                                               'correct_index': 0,
                                               'hint': 'Check the main category of this node.'},
                                              {'question': 'Which of these eras is most closely associated with Space '
                                                           'Exploration?',
                                               'options': ['1957 – Present', '2099 - Present', '10,000 BCE', 'Unknown'],
                                               'correct_index': 0,
                                               'hint': 'Think about the timeline of this topic.'},
                                              {'question': 'Which of the following is considered a related topic to '
                                                           'Space Exploration?',
                                               'options': ['Quantum Physics',
                                                           'Alien Abductions',
                                                           'Baking Bread',
                                                           'The Matrix'],
                                               'correct_index': 0,
                                               'hint': 'Look for the most logically connected topic.'},
                                              {'question': 'Did Space Exploration have a profound impact on human '
                                                           'knowledge?',
                                               'options': ['Yes, absolutely',
                                                           'No, not really',
                                                           'Only mildly',
                                                           'It was completely forgotten'],
                                               'correct_index': 0,
                                               'hint': "It's in this encyclopedia for a reason!"}],
                       'related_topics': ['Quantum Physics', 'Silicon Valley', 'Industrial Revolution']},
 'quantum physics': {'title': 'Quantum Physics',
                     'category': 'Science',
                     'era': '1900 – Present',
                     'wiki_query': 'Quantum_mechanics',
                     'coordinates': {'lat': 52.52, 'lng': 13.405},
                     'summary': 'Quantum Mechanics is a fundamental theory in physics that provides a description of '
                                'the physical properties of nature at the scale of atoms and subatomic particles. It '
                                'forms the basis for quantum chemistry, quantum field theory, and quantum computing.',
                     'milestones': [{'year': '1900',
                                     'event': 'Max Planck proposes that energy is radiated in discrete quanta.'},
                                    {'year': '1927',
                                     'event': 'Werner Heisenberg formulates the Uncertainty Principle.'},
                                    {'year': '1981',
                                     'event': 'Richard Feynman proposes the concept of a quantum computer.'}],
                     'trivia': "Schrödinger's famous cat thought experiment was actually designed to show how absurd "
                               'quantum superposition is when applied to macroscopic objects!',
                     'mindmaze_questions': [{'question': 'Which principle states that it is impossible to '
                                                         'simultaneously know exactly both the momentum and position '
                                                         'of a particle?',
                                             'options': ['Heisenberg Uncertainty Principle',
                                                         'Pauli Exclusion Principle',
                                                         'Theory of Relativity',
                                                         'Bohr Model'],
                                             'correct_index': 0,
                                             'hint': 'Named after the German physicist Werner.'},
                                            {'question': 'True or False: Quantum Physics is primarily categorized '
                                                         'under Science?',
                                             'options': ['True', 'False'],
                                             'correct_index': 0,
                                             'hint': 'Check the main category of this node.'},
                                            {'question': 'Which of these eras is most closely associated with Quantum '
                                                         'Physics?',
                                             'options': ['1900 – Present', '2099 - Present', '10,000 BCE', 'Unknown'],
                                             'correct_index': 0,
                                             'hint': 'Think about the timeline of this topic.'},
                                            {'question': 'Which of the following is considered a related topic to '
                                                         'Quantum Physics?',
                                             'options': ['Space Exploration',
                                                         'Alien Abductions',
                                                         'Baking Bread',
                                                         'The Matrix'],
                                             'correct_index': 0,
                                             'hint': 'Look for the most logically connected topic.'},
                                            {'question': 'Did Quantum Physics have a profound impact on human '
                                                         'knowledge?',
                                             'options': ['Yes, absolutely',
                                                         'No, not really',
                                                         'Only mildly',
                                                         'It was completely forgotten'],
                                             'correct_index': 0,
                                             'hint': "It's in this encyclopedia for a reason!"}],
                     'related_topics': ['Space Exploration', 'Silicon Valley', 'Artificial Intelligence']},
 'silicon valley': {'title': 'Silicon Valley',
                    'category': 'Technology',
                    'era': '1939 – Present',
                    'wiki_query': 'Silicon_Valley',
                    'coordinates': {'lat': 37.3875, 'lng': -122.0575},
                    'summary': 'Silicon Valley is a region in Northern California that serves as a global center for '
                               "high technology and innovation. It is home to many of the world's largest high-tech "
                               'corporations, thousands of startup companies, and is synonymous with the dot-com boom.',
                    'milestones': [{'year': '1939', 'event': 'Hewlett-Packard is founded in a Palo Alto garage.'},
                                   {'year': '1971',
                                    'event': 'Intel releases the 4004, the first commercially available '
                                             'microprocessor.'},
                                   {'year': '2007',
                                    'event': 'Apple releases the first iPhone, revolutionizing mobile computing.'}],
                    'trivia': "The term 'Silicon Valley' was coined in 1971 by journalist Don Hoefler to describe the "
                              'high concentration of silicon chip innovators in the region.',
                    'mindmaze_questions': [{'question': 'Which element gives Silicon Valley its name?',
                                            'options': ['Silicon', 'Carbon', 'Gold', 'Copper'],
                                            'correct_index': 0,
                                            'hint': 'It is a semiconductor crucial for making computer chips.'},
                                           {'question': 'True or False: Silicon Valley is primarily categorized under '
                                                        'Technology?',
                                            'options': ['True', 'False'],
                                            'correct_index': 0,
                                            'hint': 'Check the main category of this node.'},
                                           {'question': 'Which of these eras is most closely associated with Silicon '
                                                        'Valley?',
                                            'options': ['1939 – Present', '2099 - Present', '10,000 BCE', 'Unknown'],
                                            'correct_index': 0,
                                            'hint': 'Think about the timeline of this topic.'},
                                           {'question': 'Which of the following is considered a related topic to '
                                                        'Silicon Valley?',
                                            'options': ['Industrial Revolution',
                                                        'Alien Abductions',
                                                        'Baking Bread',
                                                        'The Matrix'],
                                            'correct_index': 0,
                                            'hint': 'Look for the most logically connected topic.'},
                                           {'question': 'Did Silicon Valley have a profound impact on human knowledge?',
                                            'options': ['Yes, absolutely',
                                                        'No, not really',
                                                        'Only mildly',
                                                        'It was completely forgotten'],
                                            'correct_index': 0,
                                            'hint': "It's in this encyclopedia for a reason!"}],
                    'related_topics': ['Industrial Revolution',
                                       'Microsoft Encarta',
                                       'Artificial Intelligence',
                                       'Quantum Physics']},
 'artificial intelligence': {'title': 'Artificial Intelligence',
                             'category': 'Technology',
                             'era': '1956 – Present',
                             'wiki_query': 'Artificial_intelligence',
                             'coordinates': {'lat': 43.7001, 'lng': -72.2894},
                             'summary': 'Artificial intelligence (AI) is intelligence demonstrated by machines, as '
                                        'opposed to the natural intelligence displayed by animals including humans. AI '
                                        'research has been defined as the field of study of intelligent agents, which '
                                        'refers to any system that perceives its environment and takes actions that '
                                        'maximize its chance of achieving its goals.',
                             'milestones': [{'year': '1956',
                                             'event': "The term 'Artificial Intelligence' is coined at the Dartmouth "
                                                      'Conference.'},
                                            {'year': '1997',
                                             'event': "IBM's Deep Blue defeats World Chess Champion Garry Kasparov."},
                                            {'year': '2022',
                                             'event': 'Widespread release of Large Language Models (LLMs) like '
                                                      'ChatGPT.'}],
                             'trivia': 'The first AI chatbot, ELIZA, was created at MIT in 1966 and acted like a '
                                       'Rogerian psychotherapist by parroting user input back at them!',
                             'mindmaze_questions': [{'question': 'At which 1956 academic conference was the term '
                                                                 "'Artificial Intelligence' officially coined?",
                                                     'options': ['Dartmouth Conference',
                                                                 'Geneva Convention',
                                                                 'Macy Conferences',
                                                                 'Solvay Conference'],
                                                     'correct_index': 0,
                                                     'hint': 'An Ivy League university located in New Hampshire.'},
                                                    {'question': 'True or False: Artificial Intelligence is primarily '
                                                                 'categorized under Technology?',
                                                     'options': ['True', 'False'],
                                                     'correct_index': 0,
                                                     'hint': 'Check the main category of this node.'},
                                                    {'question': 'Which of these eras is most closely associated with '
                                                                 'Artificial Intelligence?',
                                                     'options': ['1956 – Present',
                                                                 '2099 - Present',
                                                                 '10,000 BCE',
                                                                 'Unknown'],
                                                     'correct_index': 0,
                                                     'hint': 'Think about the timeline of this topic.'},
                                                    {'question': 'Which of the following is considered a related topic '
                                                                 'to Artificial Intelligence?',
                                                     'options': ['Silicon Valley',
                                                                 'Alien Abductions',
                                                                 'Baking Bread',
                                                                 'The Matrix'],
                                                     'correct_index': 0,
                                                     'hint': 'Look for the most logically connected topic.'},
                                                    {'question': 'Did Artificial Intelligence have a profound impact '
                                                                 'on human knowledge?',
                                                     'options': ['Yes, absolutely',
                                                                 'No, not really',
                                                                 'Only mildly',
                                                                 'It was completely forgotten'],
                                                     'correct_index': 0,
                                                     'hint': "It's in this encyclopedia for a reason!"}],
                             'related_topics': ['Silicon Valley', 'Quantum Physics', 'Microsoft Encarta']},
 'french revolution': {'title': 'French Revolution',
                       'category': 'History',
                       'era': '1789 – 1799',
                       'wiki_query': 'French_Revolution',
                       'coordinates': {'lat': 48.8566, 'lng': 2.3522},
                       'summary': 'The French Revolution was a period of radical political and societal change in '
                                  'France that began with the Estates General of 1789 and ended with the formation of '
                                  'the French Consulate in November 1799. Many of its ideas are considered fundamental '
                                  'principles of Western liberal democracy.',
                       'milestones': [{'year': '1789',
                                       'event': 'Storming of the Bastille and the Declaration of the Rights of Man.'},
                                      {'year': '1793',
                                       'event': 'Execution of King Louis XVI and the Reign of Terror begins.'},
                                      {'year': '1799', 'event': "Napoleon Bonaparte seizes power in a coup d'état."}],
                       'trivia': 'The guillotine was adopted because it was seen as a more humane, egalitarian method '
                                 'of execution compared to the gruesome methods of the past.',
                       'mindmaze_questions': [{'question': 'Which fortress-prison was famously stormed on July 14, '
                                                           '1789?',
                                               'options': ['The Bastille',
                                                           'The Louvre',
                                                           'Versailles',
                                                           'Tower of London'],
                                               'correct_index': 0,
                                               'hint': 'It became a major symbol of the French Republic.'},
                                              {'question': 'True or False: French Revolution is primarily categorized '
                                                           'under History?',
                                               'options': ['True', 'False'],
                                               'correct_index': 0,
                                               'hint': 'Check the main category of this node.'},
                                              {'question': 'Which of these eras is most closely associated with French '
                                                           'Revolution?',
                                               'options': ['1789 – 1799', '2099 - Present', '10,000 BCE', 'Unknown'],
                                               'correct_index': 0,
                                               'hint': 'Think about the timeline of this topic.'},
                                              {'question': 'Which of the following is considered a related topic to '
                                                           'French Revolution?',
                                               'options': ['Ancient Rome',
                                                           'Alien Abductions',
                                                           'Baking Bread',
                                                           'The Matrix'],
                                               'correct_index': 0,
                                               'hint': 'Look for the most logically connected topic.'},
                                              {'question': 'Did French Revolution have a profound impact on human '
                                                           'knowledge?',
                                               'options': ['Yes, absolutely',
                                                           'No, not really',
                                                           'Only mildly',
                                                           'It was completely forgotten'],
                                               'correct_index': 0,
                                               'hint': "It's in this encyclopedia for a reason!"}],
                       'related_topics': ['Ancient Rome', 'Industrial Revolution', 'Age of Discovery']},
 'impressionism': {'title': 'Impressionism',
                   'category': 'Art & Culture',
                   'era': '1860s – 1890s',
                   'wiki_query': 'Impressionism',
                   'coordinates': {'lat': 48.8606, 'lng': 2.3376},
                   'summary': 'Impressionism is a 19th-century art movement characterized by relatively small, thin, '
                              'yet visible brush strokes, open composition, emphasis on accurate depiction of light in '
                              'its changing qualities (often accentuating the effects of the passage of time), and '
                              'ordinary subject matter.',
                   'milestones': [{'year': '1874',
                                   'event': 'The first independent exhibition of Impressionist painters in Paris.'},
                                  {'year': '1889',
                                   'event': "Vincent van Gogh paints 'The Starry Night' (Post-Impressionism)."}],
                   'trivia': "The movement got its name from Claude Monet's painting 'Impression, Sunrise', which a "
                             'critic initially used as an insult!',
                   'mindmaze_questions': [{'question': "Which artist's painting 'Impression, Sunrise' gave the "
                                                       'Impressionist movement its name?',
                                           'options': ['Claude Monet',
                                                       'Pierre-Auguste Renoir',
                                                       'Edgar Degas',
                                                       'Paul Cézanne'],
                                           'correct_index': 0,
                                           'hint': 'He is famous for his paintings of water lilies.'},
                                          {'question': 'True or False: Impressionism is primarily categorized under '
                                                       'Art & Culture?',
                                           'options': ['True', 'False'],
                                           'correct_index': 0,
                                           'hint': 'Check the main category of this node.'},
                                          {'question': 'Which of these eras is most closely associated with '
                                                       'Impressionism?',
                                           'options': ['1860s – 1890s', '2099 - Present', '10,000 BCE', 'Unknown'],
                                           'correct_index': 0,
                                           'hint': 'Think about the timeline of this topic.'},
                                          {'question': 'Which of the following is considered a related topic to '
                                                       'Impressionism?',
                                           'options': ['Renaissance Florence',
                                                       'Alien Abductions',
                                                       'Baking Bread',
                                                       'The Matrix'],
                                           'correct_index': 0,
                                           'hint': 'Look for the most logically connected topic.'},
                                          {'question': 'Did Impressionism have a profound impact on human knowledge?',
                                           'options': ['Yes, absolutely',
                                                       'No, not really',
                                                       'Only mildly',
                                                       'It was completely forgotten'],
                                           'correct_index': 0,
                                           'hint': "It's in this encyclopedia for a reason!"}],
                   'related_topics': ['Renaissance Florence', 'French Revolution']},
 'dna structure': {'title': 'DNA Structure',
                   'category': 'Science',
                   'era': '1953 – Present',
                   'wiki_query': 'DNA',
                   'coordinates': {'lat': 52.2053, 'lng': 0.1218},
                   'summary': 'Deoxyribonucleic acid (DNA) is a polymer composed of two polynucleotide chains that '
                              'coil around each other to form a double helix. The polymer carries genetic instructions '
                              'for the development, functioning, growth and reproduction of all known organisms and '
                              'many viruses.',
                   'milestones': [{'year': '1953',
                                   'event': 'Watson and Crick publish the double helix structure of DNA.'},
                                  {'year': '2003', 'event': 'The Human Genome Project is declared complete.'}],
                   'trivia': 'If you unraveled all the DNA in your body, it would stretch to the sun and back over 600 '
                             'times!',
                   'mindmaze_questions': [{'question': 'What shape best describes the structure of a DNA molecule?',
                                           'options': ['Double helix', 'Single strand', 'Triple helix', 'Spherical'],
                                           'correct_index': 0,
                                           'hint': 'It looks like a twisted ladder.'},
                                          {'question': 'True or False: DNA Structure is primarily categorized under '
                                                       'Science?',
                                           'options': ['True', 'False'],
                                           'correct_index': 0,
                                           'hint': 'Check the main category of this node.'},
                                          {'question': 'Which of these eras is most closely associated with DNA '
                                                       'Structure?',
                                           'options': ['1953 – Present', '2099 - Present', '10,000 BCE', 'Unknown'],
                                           'correct_index': 0,
                                           'hint': 'Think about the timeline of this topic.'},
                                          {'question': 'Which of the following is considered a related topic to DNA '
                                                       'Structure?',
                                           'options': ['Space Exploration',
                                                       'Alien Abductions',
                                                       'Baking Bread',
                                                       'The Matrix'],
                                           'correct_index': 0,
                                           'hint': 'Look for the most logically connected topic.'},
                                          {'question': 'Did DNA Structure have a profound impact on human knowledge?',
                                           'options': ['Yes, absolutely',
                                                       'No, not really',
                                                       'Only mildly',
                                                       'It was completely forgotten'],
                                           'correct_index': 0,
                                           'hint': "It's in this encyclopedia for a reason!"}],
                   'related_topics': ['Space Exploration', 'Quantum Physics', 'Artificial Intelligence']},
 'world war ii': {'title': 'World War II',
                  'category': 'History',
                  'era': '1939 – 1945',
                  'wiki_query': 'World_War_II',
                  'coordinates': {'lat': 52.52, 'lng': 13.405},
                  'summary': 'World War II was a global conflict that lasted from 1939 to 1945. It involved the vast '
                             "majority of the world's countries forming two opposing military alliances: the Allies "
                             'and the Axis. It remains the deadliest conflict in human history.',
                  'milestones': [{'year': '1939',
                                  'event': 'Germany invades Poland, prompting Britain and France to declare war.'},
                                 {'year': '1941', 'event': 'Attack on Pearl Harbor; USA enters the war.'},
                                 {'year': '1945', 'event': 'Atomic bombings of Hiroshima and Nagasaki end the war.'}],
                  'trivia': 'During WWII, the British created a myth that eating carrots improved night vision to hide '
                            'the fact they had invented radar!',
                  'mindmaze_questions': [{'question': 'The invasion of which country by Germany in 1939 triggered the '
                                                      'start of World War II in Europe?',
                                          'options': ['Poland', 'France', 'Austria', 'Czechoslovakia'],
                                          'correct_index': 0,
                                          'hint': 'Located between Germany and the Soviet Union.'},
                                         {'question': 'True or False: World War II is primarily categorized under '
                                                      'History?',
                                          'options': ['True', 'False'],
                                          'correct_index': 0,
                                          'hint': 'Check the main category of this node.'},
                                         {'question': 'Which of these eras is most closely associated with World War '
                                                      'II?',
                                          'options': ['1939 – 1945', '2099 - Present', '10,000 BCE', 'Unknown'],
                                          'correct_index': 0,
                                          'hint': 'Think about the timeline of this topic.'},
                                         {'question': 'Which of the following is considered a related topic to World '
                                                      'War II?',
                                          'options': ['Industrial Revolution',
                                                      'Alien Abductions',
                                                      'Baking Bread',
                                                      'The Matrix'],
                                          'correct_index': 0,
                                          'hint': 'Look for the most logically connected topic.'},
                                         {'question': 'Did World War II have a profound impact on human knowledge?',
                                          'options': ['Yes, absolutely',
                                                      'No, not really',
                                                      'Only mildly',
                                                      'It was completely forgotten'],
                                          'correct_index': 0,
                                          'hint': "It's in this encyclopedia for a reason!"}],
                  'related_topics': ['Industrial Revolution', 'Space Exploration', 'Artificial Intelligence']},
 'the internet': {'title': 'The Internet',
                  'category': 'Technology',
                  'era': '1969 – Present',
                  'wiki_query': 'Internet',
                  'coordinates': {'lat': 38.8951, 'lng': -77.0364},
                  'summary': 'The Internet is the global system of interconnected computer networks that uses the '
                             'Internet protocol suite (TCP/IP) to communicate between networks and devices. It '
                             'originated with ARPANET in the 1960s and evolved into the World Wide Web in the 1990s.',
                  'milestones': [{'year': '1969', 'event': 'The first ARPANET message is sent between UCLA and SRI.'},
                                 {'year': '1989', 'event': 'Tim Berners-Lee invents the World Wide Web at CERN.'},
                                 {'year': '1993',
                                  'event': 'Mosaic, the first popular graphical web browser, is released.'}],
                  'trivia': "The first message ever sent over the ARPANET was meant to be 'LOGIN', but the system "
                            "crashed after typing 'LO', making the first message 'LO'!",
                  'mindmaze_questions': [{'question': 'Who is credited with inventing the World Wide Web in 1989?',
                                          'options': ['Tim Berners-Lee', 'Al Gore', 'Bill Gates', 'Vint Cerf'],
                                          'correct_index': 0,
                                          'hint': 'He was working at CERN in Switzerland.'},
                                         {'question': 'True or False: The Internet is primarily categorized under '
                                                      'Technology?',
                                          'options': ['True', 'False'],
                                          'correct_index': 0,
                                          'hint': 'Check the main category of this node.'},
                                         {'question': 'Which of these eras is most closely associated with The '
                                                      'Internet?',
                                          'options': ['1969 – Present', '2099 - Present', '10,000 BCE', 'Unknown'],
                                          'correct_index': 0,
                                          'hint': 'Think about the timeline of this topic.'},
                                         {'question': 'Which of the following is considered a related topic to The '
                                                      'Internet?',
                                          'options': ['Silicon Valley',
                                                      'Alien Abductions',
                                                      'Baking Bread',
                                                      'The Matrix'],
                                          'correct_index': 0,
                                          'hint': 'Look for the most logically connected topic.'},
                                         {'question': 'Did The Internet have a profound impact on human knowledge?',
                                          'options': ['Yes, absolutely',
                                                      'No, not really',
                                                      'Only mildly',
                                                      'It was completely forgotten'],
                                          'correct_index': 0,
                                          'hint': "It's in this encyclopedia for a reason!"}],
                  'related_topics': ['Silicon Valley', 'Microsoft Encarta', 'Artificial Intelligence']},
 'the beatles': {'title': 'The Beatles',
                 'category': 'Art & Culture',
                 'era': '1960 – 1970',
                 'wiki_query': 'The_Beatles',
                 'coordinates': {'lat': 53.4084, 'lng': -2.9916},
                 'summary': 'The Beatles were an English rock band formed in Liverpool in 1960. Comprising John '
                            'Lennon, Paul McCartney, George Harrison, and Ringo Starr, they are regarded as the most '
                            'influential band of all time, revolutionizing music production and pop culture.',
                 'milestones': [{'year': '1962', 'event': "Release of their first hit single, 'Love Me Do'."},
                                {'year': '1964',
                                 'event': "The Beatles appear on The Ed Sullivan Show in the US ('British Invasion')."},
                                {'year': '1969',
                                 'event': 'The final live performance on the roof of Apple Corps in London.'}],
                 'trivia': 'None of the Beatles could read or write traditional sheet music; they composed everything '
                           'by ear!',
                 'mindmaze_questions': [{'question': 'Which English city did The Beatles originally form in?',
                                         'options': ['Liverpool', 'London', 'Manchester', 'Birmingham'],
                                         'correct_index': 0,
                                         'hint': 'A maritime city in northwest England.'},
                                        {'question': 'True or False: The Beatles is primarily categorized under Art & '
                                                     'Culture?',
                                         'options': ['True', 'False'],
                                         'correct_index': 0,
                                         'hint': 'Check the main category of this node.'},
                                        {'question': 'Which of these eras is most closely associated with The Beatles?',
                                         'options': ['1960 – 1970', '2099 - Present', '10,000 BCE', 'Unknown'],
                                         'correct_index': 0,
                                         'hint': 'Think about the timeline of this topic.'},
                                        {'question': 'Which of the following is considered a related topic to The '
                                                     'Beatles?',
                                         'options': ['Impressionism', 'Alien Abductions', 'Baking Bread', 'The Matrix'],
                                         'correct_index': 0,
                                         'hint': 'Look for the most logically connected topic.'},
                                        {'question': 'Did The Beatles have a profound impact on human knowledge?',
                                         'options': ['Yes, absolutely',
                                                     'No, not really',
                                                     'Only mildly',
                                                     'It was completely forgotten'],
                                         'correct_index': 0,
                                         'hint': "It's in this encyclopedia for a reason!"}],
                 'related_topics': ['Impressionism', 'Renaissance Florence', 'The Internet']},
 'cyberpunk': {'title': 'Cyberpunk',
               'category': 'Art & Culture',
               'era': '1980s – Present',
               'wiki_query': 'Cyberpunk',
               'coordinates': {'lat': 35.6762, 'lng': 139.6503},
               'summary': 'Cyberpunk is a subgenre of science fiction in a dystopian futuristic setting that tends to '
                          "focus on a 'combination of lowlife and high tech'. It features advanced technological and "
                          'scientific achievements, such as artificial intelligence and cybernetics, juxtaposed with a '
                          'degree of breakdown or radical change in the social order.',
               'milestones': [{'year': '1982', 'event': "Release of the highly influential film 'Blade Runner'."},
                              {'year': '1984',
                               'event': "William Gibson publishes the seminal cyberpunk novel 'Neuromancer'."},
                              {'year': '1999',
                               'event': "Release of 'The Matrix', bringing cyberpunk to mainstream blockbusters."}],
               'trivia': "William Gibson coined the term 'cyberspace' in his writing before the World Wide Web even "
                         'existed!',
               'mindmaze_questions': [{'question': 'Which 1984 novel by William Gibson is considered the '
                                                   'quintessential cyberpunk work?',
                                       'options': ['Neuromancer',
                                                   'Snow Crash',
                                                   'Do Androids Dream of Electric Sheep?',
                                                   '1984'],
                                       'correct_index': 0,
                                       'hint': "The title refers to a hacker who interfaces with the global 'matrix'."},
                                      {'question': 'True or False: Cyberpunk is primarily categorized under Art & '
                                                   'Culture?',
                                       'options': ['True', 'False'],
                                       'correct_index': 0,
                                       'hint': 'Check the main category of this node.'},
                                      {'question': 'Which of these eras is most closely associated with Cyberpunk?',
                                       'options': ['1980s – Present', '2099 - Present', '10,000 BCE', 'Unknown'],
                                       'correct_index': 0,
                                       'hint': 'Think about the timeline of this topic.'},
                                      {'question': 'Which of the following is considered a related topic to Cyberpunk?',
                                       'options': ['Artificial Intelligence',
                                                   'Alien Abductions',
                                                   'Baking Bread',
                                                   'The Matrix'],
                                       'correct_index': 0,
                                       'hint': 'Look for the most logically connected topic.'},
                                      {'question': 'Did Cyberpunk have a profound impact on human knowledge?',
                                       'options': ['Yes, absolutely',
                                                   'No, not really',
                                                   'Only mildly',
                                                   'It was completely forgotten'],
                                       'correct_index': 0,
                                       'hint': "It's in this encyclopedia for a reason!"}],
               'related_topics': ['Artificial Intelligence', 'The Internet', 'Silicon Valley', 'Microsoft Encarta']}}



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


def generate_node_structure_with_gemma(topic: str, wiki: str, client, types) -> Dict[str, Any]:
    """
    Call gemma-4-31b with High Thinking to create the node structure from the topic & article details.
    """
    wiki_context = f"\nAnchor the generation based on this Wikipedia URL/Title: '{wiki}'" if wiki else ""
    prompt = f"""
You are the knowledge engine for 'Encarta 2.0 (NewGen Retro Edition)'.
Analyze the topic/article: '{topic}'.{wiki_context}

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
Generate 5 engaging trivia questions for the MindMaze dungeon game for topic '{topic}'.
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
  }},
  {{
    "question": "<Fill in the blank or timeline trivia text>",
    "options": ["<Option A>", "<Option B>", "<Option C>", "<Option D>"],
    "correct_index": <0, 1, 2, or 3>,
    "hint": "<Helpful hint>"
  }},
  {{
    "question": "<Odd one out trivia text>",
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


_genai_client = None

# Ensure DB table exists and is seeded on module load
init_db(force_reset=False)

def get_article(topic: str, wiki: str = None) -> ArticleResponse:
    """
    Main article retrieval pipeline:
    1. Check SQLite Cache
    2. Check Mock Mode
    3. Use gemma-4-31b with High Thinking to create Node Structure
    4. Use gemini-2.5-flash to generate MindMaze Quiz
    5. Save node into SQLite database & return.
    """
    global _genai_client
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

    if _genai_client is None:
        _genai_client = genai.Client(api_key=api_key)

    # Step 1: Create Node Structure using gemma-4-31b model at High Thinking
    node_data = generate_node_structure_with_gemma(topic, wiki, _genai_client, types)

    # Step 2: Generate MindMaze Quiz using gemini-2.5-flash model
    quiz_questions = generate_quiz_with_flash(topic, node_data.get("summary", ""), _genai_client, types)
    node_data["mindmaze_questions"] = quiz_questions

    # Save to SQLite database (article_cache & knowledge_nodes tables)
    save_cached_article(topic, node_data)
    return ArticleResponse(**node_data)

