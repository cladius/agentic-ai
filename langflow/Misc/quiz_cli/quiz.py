#!/usr/bin/env python3
"""
CLI MCQ Quiz App
A simple command-line application that fetches MCQ questions from your Langflow API
and provides an interactive quiz experience with scoring.
"""

import requests
import json
import os
import sys
import re
from typing import List, Dict, Any

class MCQQuiz:
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key
        self.headers = {
            'Content-Type': 'application/json',
            'x-api-key': api_key
        }
    
    def fetch_questions(self, topic: str) -> List[Dict[str, Any]]:
        """Fetch MCQ questions from the Langflow API"""
        payload = {
            "output_type": "chat",
            "input_type": "chat",
            "input_value": topic
        }
        
        try:
            print(f"🔄 Generating questions about '{topic}'...")
            response = requests.post(self.api_url, json=payload, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract the text content from the response
            text_content = data["outputs"][0]["outputs"][0]["results"]["message"]["data"]["text"]
            
            # Extract JSON from the markdown code block
            json_match = re.search(r'```json\n(.*?)\n```', text_content, re.DOTALL)
            if json_match:
                questions_json = json_match.group(1)
                questions = json.loads(questions_json)
                return questions
            else:
                raise ValueError("Could not extract JSON from response")
                
        except requests.RequestException as e:
            print(f"❌ Error fetching questions: {e}")
            sys.exit(1)
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            print(f"❌ Error parsing response: {e}")
            sys.exit(1)
    
    def display_question(self, question_data: Dict[str, Any], question_num: int) -> None:
        """Display a single question with options"""
        print(f"\n📝 Question {question_num}/10:")
        print(f"   {question_data['question']}")
        print()
        
        for i, option in enumerate(question_data['options']):
            print(f"   {chr(65 + i)}. {option}")
    
    def get_user_answer(self) -> int:
        """Get user's answer choice"""
        while True:
            try:
                answer = input("\n   Your answer (A/B/C/D): ").upper().strip()
                if answer in ['A', 'B', 'C', 'D']:
                    return ord(answer) - ord('A')  # Convert A,B,C,D to 0,1,2,3
                else:
                    print("   ⚠️  Please enter A, B, C, or D")
            except KeyboardInterrupt:
                print("\n\n👋 Quiz cancelled. Goodbye!")
                sys.exit(0)
    
    def show_result(self, is_correct: bool, correct_answer: int, options: List[str]) -> None:
        """Show whether the answer was correct"""
        if is_correct:
            print("   ✅ Correct!")
        else:
            print(f"   ❌ Wrong! The correct answer was: {chr(65 + correct_answer)}. {options[correct_answer]}")
    
    def run_quiz(self, topic: str) -> None:
        """Run the complete quiz"""
        print("🎯 MCQ Quiz Generator")
        print("=" * 50)
        
        # Fetch questions
        questions = self.fetch_questions(topic)
        
        if len(questions) != 10:
            print(f"⚠️  Warning: Expected 10 questions, got {len(questions)}")
        
        score = 0
        total_questions = len(questions)
        
        print(f"\n🚀 Starting quiz on '{topic}' with {total_questions} questions!")
        print("   (Press Ctrl+C to exit at any time)")
        
        # Ask each question
        for i, question_data in enumerate(questions, 1):
            self.display_question(question_data, i)
            user_answer = self.get_user_answer()
            correct_answer = question_data['correct_answer']
            
            is_correct = user_answer == correct_answer
            if is_correct:
                score += 1
            
            self.show_result(is_correct, correct_answer, question_data['options'])
        
        # Show final score
        self.show_final_score(score, total_questions)
    
    def show_final_score(self, score: int, total: int) -> None:
        """Display the final score with some encouragement"""
        percentage = (score / total) * 100
        
        print("\n" + "=" * 50)
        print("🎉 QUIZ COMPLETED!")
        print(f"📊 Your Score: {score}/{total} ({percentage:.1f}%)")
        
        if percentage >= 90:
            print("🌟 Outstanding! You're an expert!")
        elif percentage >= 80:
            print("👍 Great job! Well done!")
        elif percentage >= 70:
            print("😊 Good work! Keep it up!")
        elif percentage >= 60:
            print("📚 Not bad! A bit more study and you'll ace it!")
        else:
            print("💪 Keep learning! Practice makes perfect!")
        
        print("=" * 50)


def main():
    """Main function to run the CLI app"""
    # Get API configuration from environment variables
    api_key = os.getenv('LANGFLOW_API_KEY')
    if not api_key:
        print("❌ Error: LANGFLOW_API_KEY environment variable not set")
        print("   Set it with: export LANGFLOW_API_KEY='your-api-key'")
        sys.exit(1)
    
    # API URL (you can modify this if needed)
    api_url = 'http://localhost:7860/api/v1/run/973c0769-772b-4036-9c9f-29bb272ea4f3?stream=false'
    
    # Get topic from command line argument or prompt user
    if len(sys.argv) > 1:
        topic = ' '.join(sys.argv[1:])
    else:
        try:
            topic = input("📚 Enter the topic for your quiz: ").strip()
            if not topic:
                print("❌ Topic cannot be empty")
                sys.exit(1)
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            sys.exit(0)
    
    # Create and run the quiz
    quiz = MCQQuiz(api_url, api_key)
    quiz.run_quiz(topic)


if __name__ == "__main__":
    main()
