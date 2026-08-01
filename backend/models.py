from typing import List
from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    lat: float = Field(..., description="Latitude coordinate")
    lng: float = Field(..., description="Longitude coordinate")


class Milestone(BaseModel):
    year: str = Field(..., description="Year or time frame of the historical milestone")
    event: str = Field(..., description="Description of the key event")


class MindMazeQuestion(BaseModel):
    question: str = Field(..., description="Trivia question text")
    options: List[str] = Field(..., description="Four multiple choice options")
    correct_index: int = Field(..., description="0-based index of the correct option")
    hint: str = Field(..., description="Helpful hint if the player guesses incorrectly")


class ArticleResponse(BaseModel):
    title: str = Field(..., description="Title of the topic/article")
    era: str = Field(..., description="Era, century, or time period stamp")
    wiki_query: str = Field(..., description="Query parameter string for Wikipedia REST API")
    coordinates: Coordinates = Field(..., description="Geographical coordinates for 3D Globe alignment")
    summary: str = Field(..., description="Generative high-level summary")
    milestones: List[Milestone] = Field(..., description="Horizontal timeline milestones")
    trivia: str = Field(..., description="Interactive 'Did You Know?' trivia fact")
    mindmaze_questions: List[MindMazeQuestion] = Field(..., description="List of 3-5 MindMaze dungeon trivia questions")
    related_topics: List[str] = Field(..., description="List of related node topic titles")


class SeedTopic(BaseModel):
    id: str
    title: str
    category: str
    era: str
    lat: float
    lng: float
    summary_short: str
