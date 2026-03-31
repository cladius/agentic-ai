import json
import boto3
import uuid
import tempfile
import os
from typing import List, Dict
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
bedrock_runtime = boto3.client('bedrock-runtime')
polly_client = boto3.client('polly')
s3_client = boto3.client('s3')

# Configuration
BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'level5-audio-podcast')
BEDROCK_MODEL_ID = 'anthropic.claude-3-sonnet-20240229-v1:0'
MALE_VOICE = 'Matthew'  # Polly voice ID
FEMALE_VOICE = 'Joanna'  # Polly voice ID

def lambda_handler(event, context):
    """
    Main Lambda handler function
    """
    try:
        logger.info(f"Processing event: {event}")

        # Extract content.document from event
        content = event['node']['inputs'][0]['value']
        if not content:
            raise ValueError("No content provided")
        
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        logger.info(f"Processing session: {session_id}")
        
        # Step 1: Generate podcast script using Bedrock
        logger.info("Generating podcast script with Bedrock...")
        podcast_script = generate_podcast_script(content)
        
        # Step 2: Generate audio segments and upload to S3
        logger.info("Generating audio segments with Polly...")
        audio_segments = generate_audio_segments(podcast_script, session_id)
        final_audio_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{session_id}/final_podcast.mp3"
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'final_audio_url': final_audio_url,
                'script': podcast_script
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }

def generate_podcast_script(content: str) -> List[Dict]:
    """
    Generate podcast script using Bedrock
    """
    prompt = f"""
    You are a scriptwriter creating a two-person podcast transcript based on the input text below. 
    Your goal is to transform the content into a natural, engaging conversation between two hosts. 
    Do NOT use SSML syntax.
    Format the response as a JSON array where each element represents a speaker turn with the following structure:
    
    {{
        "speaker": "host1" or "host2",
        "text": "The spoken text"
    }}
    
    Guidelines:
    - host1 is male, host2 is female
    - Make the conversation flow naturally with back-and-forth discussion
    - Keep individual segments reasonably short (1-3 sentences each)
    - Include introductory and concluding segments
    - Make it informative but conversational
    - Light, natural banter and humour.
    - Occasional questions, affirmations, and reactions (e.g., “Really?”, “That’s wild!”, “Exactly!”).
    - A clear flow of ideas but without sounding like a lecture.
    - Personality and warmth in the way each host speaks.
    - Differences in voice and style between the two speakers (e.g., one might be more curious, the other more knowledgeable or witty).
    - Keep it enjoyable and easy to listen to, like something you’d hear on a popular podcast. Avoid making it sound robotic or scripted.
    
    Content to discuss:
    {content}
    
    Return only the JSON array, no additional text.
    """
    
    try:
        # Prepare the request for Bedrock
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4000,
            "messages": [
                {
                    "role": "user", 
                    "content": prompt
                }
            ]
        }
        
        # Make the Bedrock API call
        response = bedrock_runtime.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps(request_body)
        )
        
        # Parse the response
        response_body = json.loads(response['body'].read())
        script_text = response_body['content'][0]['text']
        
        # Parse the JSON script
        script = json.loads(script_text)
        

        logger.info(f"Script : {script}")

        logger.info(f"Generated script with {len(script)} segments")
        return script
        
    except Exception as e:
        logger.error(f"Error generating script with Bedrock: {str(e)}")
        raise

def generate_audio_segments(script: List[Dict], session_id: str) -> List[Dict]:
    """
    Generate audio for each segment using Polly, upload each segment to S3,
    then concatenate all segments into a final mp3 using plain file IO and upload it.
    """
    audio_segments = []
    segment_bytes_list = []
    
    for i, segment in enumerate(script):
        try:
            # Determine voice based on speaker
            voice_id = MALE_VOICE if segment['speaker'] == 'host1' else FEMALE_VOICE
            
            # Generate speech with Polly
            response = polly_client.synthesize_speech(
                Text=segment['text'],
                OutputFormat='mp3',
                VoiceId=voice_id,
                TextType='ssml' if '<speak>' in segment['text'] else 'text',
                Engine='neural'  # Use neural engine for better quality
            )
            
            # Read audio bytes from the response stream
            audio_data = response['AudioStream'].read()
            segment_bytes_list.append(audio_data)
            
            # Upload individual segment to S3
            s3_key = f"{session_id}/segment_{i:03d}_{segment['speaker']}.mp3"
            s3_client.put_object(
                Bucket=BUCKET_NAME,
                Key=s3_key,
                Body=audio_data,
                ContentType='audio/mpeg'
            )
            
            audio_segments.append({
                's3_key': s3_key,
                'speaker': segment['speaker'],
                'voice_id': voice_id,
                'index': i,
                'text_preview': segment['text'][:100] + '...' if len(segment['text']) > 100 else segment['text']
            })
            
            logger.info(f"Generated and uploaded audio segment {i+1}/{len(script)} to {s3_key}")
            
        except Exception as e:
            logger.error(f"Error generating audio for segment {i}: {str(e)}")
            raise

    # Concatenate the audio segments using plain file IO
    try:
        # Create a temporary file to write the combined audio data
        temp_file_path = None
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file_path = temp_file.name
            for segment_bytes in segment_bytes_list:
                temp_file.write(segment_bytes)
        
        # Read the combined file
        with open(temp_file_path, "rb") as final_file:
            final_audio_data = final_file.read()
        
        # Define final S3 key and upload the concatenated audio file
        final_s3_key = f"{session_id}/final_podcast.mp3"
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=final_s3_key,
            Body=final_audio_data,
            ContentType='audio/mpeg'
        )
        
        logger.info(f"Uploaded final combined audio to {final_s3_key}")
        
    finally:
        # Clean up temporary file if it was created
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
    
    # Optionally, add the final audio's S3 key info to the returned segments
    audio_segments.append({'final_audio_s3_key': final_s3_key})
    return audio_segments
