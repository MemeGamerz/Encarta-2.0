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
PREBAKED_FIXTURES: Dict[str, Dict[str, Any]] = {'microsoft encarta': {'title': 'Microsoft Encarta',
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

