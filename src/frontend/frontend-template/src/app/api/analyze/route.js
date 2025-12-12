import { NextResponse } from 'next/server';
import { GoogleGenAI, Type } from '@google/genai';

const apiKey = process.env.GEMINI_API_KEY || process.env.API_KEY;
const ai = apiKey ? new GoogleGenAI({ apiKey }) : null;

const ANALYSIS_SCHEMA = {
  type: Type.OBJECT,
  properties: {
    title: { type: Type.STRING, description: 'A short, punchy headline for the incident analysis.' },
    fan_summary: { type: Type.STRING, description: 'A simplified explanation of what happened and why it matters, avoiding jargon.' },
    technical_verdict: { type: Type.STRING, description: 'The formal steward decision and technical reasoning.' },
    penalty_severity: {
      type: Type.STRING,
      enum: ['No Action', 'Warning', 'Time Penalty', 'Grid Drop', 'Disqualification'],
      description: 'The likely or actual penalty category.'
    },
    fairness_rating: { type: Type.NUMBER, description: 'A score from 0 to 100 indicating strictness. 0 is very lenient, 100 is very harsh, 50 is standard.' },
    regulations_breached: {
      type: Type.ARRAY,
      items: {
        type: Type.OBJECT,
        properties: {
          article: { type: Type.STRING, description: 'The specific FIA Sporting Code article number.' },
          description: { type: Type.STRING, description: 'The text of the rule.' },
          relevance: { type: Type.STRING, description: 'Why this rule applies here.' }
        },
        required: ['article', 'description', 'relevance']
      }
    },
    historical_precedents: {
      type: Type.ARRAY,
      items: {
        type: Type.OBJECT,
        properties: {
          driver: { type: Type.STRING, description: "The full name of the primary driver involved (e.g. 'Lewis Hamilton', 'Max Verstappen')." },
          year: { type: Type.STRING },
          race: { type: Type.STRING },
          incident: { type: Type.STRING },
          penalty: { type: Type.STRING },
          similarity_score: { type: Type.NUMBER }
        },
        required: ['driver', 'year', 'race', 'incident', 'penalty', 'similarity_score']
      }
    },
    key_factors: {
      type: Type.ARRAY,
      items: { type: Type.STRING },
      description: 'List of 3-5 key bullet points influencing the decision (e.g., "Telemetry showed no braking").'
    }
  },
  required: ['title', 'fan_summary', 'technical_verdict', 'penalty_severity', 'fairness_rating', 'regulations_breached', 'historical_precedents', 'key_factors']
};

export async function POST(request) {
  if (!ai) {
    return NextResponse.json({ error: 'GEMINI_API_KEY or API_KEY is not configured on the server.' }, { status: 500 });
  }

  let body;
  try {
    body = await request.json();
  } catch {
    body = {};
  }

  const incidentDescription = body?.incidentDescription || body?.prompt;
  if (!incidentDescription || !incidentDescription.trim()) {
    return NextResponse.json({ error: 'incidentDescription is required.' }, { status: 400 });
  }

  try {
    const response = await ai.models.generateContent({
      model: 'gemini-2.5-flash',
      contents: `You are an expert FIA Formula One Steward and Fan Explainer. Analyze the following incident description provided by a user.

Incident Description: "${incidentDescription}"

Your goal is to explain the potential or actual penalty, cite the specific FIA Sporting Regulations involved, and compare it to historical precedents to determine consistency.

Maintain a tone that is authoritative yet accessible to casual fans.`,
      config: {
        responseMimeType: 'application/json',
        responseSchema: ANALYSIS_SCHEMA,
        systemInstruction: "You are the 'Virtual Steward'. You have access to knowledge of the FIA International Sporting Code and F1 Sporting Regulations. Always be objective."
      }
    });

    const text = response.text;
    if (!text) {
      throw new Error('No response from Gemini');
    }

    const parsed = JSON.parse(text);
    return NextResponse.json(parsed);
  } catch (error) {
    console.error('Gemini analysis failed:', error);
    return NextResponse.json({ error: 'Failed to analyze incident with Gemini.' }, { status: 500 });
  }
}
