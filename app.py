
import os
from dotenv import load_dotenv
import re
import json
from fastapi import FastAPI, HTTPException
import asyncio
from pydantic import BaseModel
from typing import List
# Load environment variables
load_dotenv()

# Import LangChain
from langchain_core.messages import HumanMessage

# Google Gemini LLM
from langchain_google_genai import ChatGoogleGenerativeAI

# LangChain + Groq
from langchain_groq import ChatGroq

# OpenAI-compatible
from langchain_openai import ChatOpenAI

app = FastAPI(title="Hospital Department Recommender")

# ---------- Input Schema ----------
class PatientInput(BaseModel):
    llm: str
    gender: str
    age: int
    symptoms: List[str]

# ---------- Output Schema ----------
class RecommendationOutput(BaseModel):
    recommended_department: list[str]
    possibility_of_illness: list[str]
    initial_handling: list[str]

# ---------- Initialize LLM ----------
def get_llm(llm_name: str):
    temp = 0.2  # Default temperature
    timeout = 100  # Default timeout in seconds
    if llm_name == "gemini":
        # Initialize the LLM with the API key
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=temp,  # Lower temperature for more deterministic responses
            timeout=timeout
        )
    elif llm_name == "groq":
        llm = ChatGroq(
            # model="llama-3.1-8b-instant",
            model="groq/compound",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=temp,
            timeout=timeout
        )
    elif llm_name == "openai":
        llm = ChatOpenAI(
            model_name="gpt-5-mini",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            temperature=temp,
            timeout=timeout
        )
    else:
        raise ValueError("Unsupported LLM name")
    
    return llm

@app.post("/recommend", response_model=RecommendationOutput)
async def recommend_department(patient: PatientInput):
    """
    Recommend specialist department using Gemini via LangChain
    """
    
    # print(f"Received patient data: {patient}")
    if not patient.symptoms:
        raise HTTPException(status_code=400, detail="Symptoms list cannot be empty")
    llm = get_llm(patient.llm)
    # Compose input for the model
    prompt = (
        f"You are a hospital triage assistant. Based on the patient info below, "
        f"suggest the most relevant specialist department, possibility of illness from patient symptoms, and initial handling.\n\n"
        f"Gender: {patient.gender}\n"
        f"Age: {patient.age}\n"
        f"Symptoms: {', '.join(patient.symptoms)}\n\n"
        # f"Return ONLY the department name (e.g. Neurology, Cardiology, Gastroenterology, etc.)"
        f"Return ONLY the response in the following JSON format and in Bahasa Indonesia:\n"
        f"department: max 3 department (e.g. Neurology, Cardiology, Gastroenterology, etc.)\n"
        f"initial_handling: provide initial handling steps based on symptoms (max 3 steps).\n"
        f"possibility_of_illness: provide possible illnesses based on symptoms (max 3).\n"
    )

    try:
        response = await asyncio.wait_for(
            llm.ainvoke([HumanMessage(content=prompt)]),
            timeout=300
        )
        text = response.content.strip()
        # print({text})
        # print(type(text))
        start = text.find("{")
        end = text.rfind("}") + 1
        json_str = text[start:end]

        data = json.loads(json_str)
        # print(json_str)
        # print(data["department"])
        department = data["department"]
        initial_handling = data["initial_handling"]
        possibility_of_illness = data["possibility_of_illness"]
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="LLM request timed out after 10 seconds. Please try again later."
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM API error: {str(e)}")

    return {
            "recommended_department": department,
            "possibility_of_illness": possibility_of_illness,
            "initial_handling": initial_handling
        }
