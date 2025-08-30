from dotenv import load_dotenv
load_dotenv()

import asyncio
import json
import base64
from typing import Dict, Optional
from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect, HTTPException
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse
from twilio.rest import Client as TwilioClient
from pydantic import BaseModel
import logging
import traceback
from gemini_agent import TwilioGeminiAgent
from config import config

# Configure logging FIRST
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Validate configuration
try:
    config.validate()
    logger.info("[DEBUG] Configuration validated successfully")
except ValueError as e:
    logger.error(f"[DEBUG] Configuration error: {e}")
    exit(1)

app = FastAPI(title="Twilio-Gemini Outbound Bridge")

# Initialize Twilio client
twilio_client = TwilioClient(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)

# Store active sessions
active_sessions: Dict[str, TwilioGeminiAgent] = {}

class CallRequest(BaseModel):
    phone_number: str
    message: Optional[str] = None

@app.get("/")
async def root():
    return {"message": "Twilio-Gemini Outbound Bridge is running"}

@app.post("/make-call")
async def make_outbound_call(call_request: CallRequest):
    """Initiate an outbound call"""
    try:
        phone_number = call_request.phone_number
        if not phone_number.startswith('+'):
            phone_number = '+' + phone_number.lstrip('+')
        logger.info(f"[DEBUG] Initiating call to: {phone_number}")
        call = twilio_client.calls.create(
            to=phone_number,
            from_=config.TWILIO_PHONE_NUMBER,
            url=f'https://{config.PUBLIC_DOMAIN}/outbound-twiml',
            status_callback=f'https://{config.PUBLIC_DOMAIN}/call-status',
            record=False
        )
        logger.info(f"[DEBUG] Call initiated with SID: {call.sid}")
        return {
            "success": True,
            "call_sid": call.sid,
            "status": "initiated",
            "to": phone_number,
            "from": config.TWILIO_PHONE_NUMBER
        }
    except Exception as e:
        logger.error(f"[DEBUG] Error making call: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to make call: {str(e)}")
@app.get("/test-websocket")
async def test_websocket_info():
    return {
        "websocket_endpoint": "/media-stream",
        "full_url": f"wss://{config.PUBLIC_DOMAIN}/media-stream",
        "server_status": "running",
        "domain": config.PUBLIC_DOMAIN
    }
@app.websocket("/test-messages")
async def test_websocket_messages(websocket: WebSocket):
    await websocket.accept()
    logger.info("[DEBUG] ✅ Test WebSocket connected")
    
    try:
        # Send test message
        await websocket.send_text(json.dumps({
            "event": "test",
            "message": "WebSocket message processing works"
        }))
        
        # Listen for messages
        async for message in websocket.iter_text():
            logger.info(f"[DEBUG] 📨 Test message received: {message}")
            data = json.loads(message)
            
            # Echo back
            await websocket.send_text(json.dumps({
                "event": "echo",
                "received": data
            }))
            
    except Exception as e:
        logger.error(f"[DEBUG] Test WebSocket error: {e}")

@app.post("/outbound-twiml")
async def outbound_twiml(request: Request):
    try:
        response = VoiceResponse()
        ws_url = f"wss://{config.PUBLIC_DOMAIN}/media-stream"
        
        logger.info(f"[DEBUG] 🔗 Outbound TwiML with WebSocket: {ws_url}")
        
        # Start streaming immediately
        start = response.start()
        start.stream(url=ws_url, track="both_tracks")
        
        # Brief pause to establish connection
        response.pause(length=1)
        
        # Let the AI introduce itself
        response.say("Hello! I'm your AI assistant.")
        
        # Keep the call alive for conversation
        response.pause(length=300)
        
        twiml_content = str(response)
        logger.info(f"[DEBUG] 📋 Outbound TwiML: {twiml_content}")
        return Response(content=str(response), media_type="application/xml")
        
    except Exception as e:
        logger.error(f"[DEBUG] ❌ TwiML error: {e}")
        response = VoiceResponse()
        response.say("Connection error.")
        response.hangup()
        return Response(content=str(response), media_type="application/xml")


@app.post("/call-status")
async def call_status_callback(request: Request):
    form_data = await request.form()
    call_sid = form_data.get("CallSid")
    call_status = form_data.get("CallStatus")
    logger.info(f"[DEBUG] Call {call_sid} status: {call_status}")
    if call_status in ["completed", "busy", "no-answer", "canceled", "failed"]:
        if call_sid in active_sessions:
            agent = active_sessions[call_sid]
            await agent.stop()
            del active_sessions[call_sid]
            logger.info(f"[DEBUG] Cleaned up session for call: {call_sid}")
    return {"status": "received"}

@app.websocket("/media-stream")
async def handle_media_stream(websocket: WebSocket):
    client_ip = websocket.client.host if websocket.client else "unknown"
    logger.info(f"[DEBUG] ⭐ WebSocket connection from Twilio IP: {client_ip}")
    
    try:
        await websocket.accept()
        logger.info("[DEBUG] ✅ WebSocket connection accepted")
        
        # CRITICAL FIX: Initialize agent immediately for outbound calls
        # Generate a temporary call_sid from the WebSocket connection
        import time
        temp_call_sid = f"WS_{int(time.time())}"
        
        agent = TwilioGeminiAgent(websocket, temp_call_sid)
        active_sessions[temp_call_sid] = agent
        
        logger.info(f"[DEBUG] 🤖 Initializing agent immediately for outbound call")
        try:
            await agent.start_and_wait()
            logger.info(f"[DEBUG] ✅ Agent ready for outbound call")
        except Exception as e:
            logger.error(f"[DEBUG] ❌ Agent startup failed: {e}")
            return
        
        call_sid = None
        message_count = 0
        
        # Process incoming messages
        async for message in websocket.iter_text():
            message_count += 1
            logger.info(f"[DEBUG] 📨 Message #{message_count}: {message[:200]}...")
            
            try:
                data = json.loads(message)
                event_type = data.get("event", "unknown")
                logger.info(f"[DEBUG] 🎯 Event: {event_type}")
                
                if event_type == "start":
                    start_data = data.get("start", {})
                    call_sid = start_data.get("callSid")
                    stream_sid = start_data.get("streamSid")
                    tracks = start_data.get("tracks", [])
                    
                    logger.info(f"[DEBUG] 🚀 Stream started:")
                    logger.info(f"[DEBUG]   Call SID: {call_sid}")
                    logger.info(f"[DEBUG]   Stream SID: {stream_sid}")
                    logger.info(f"[DEBUG]   Tracks: {tracks}")
                    
                    # Update agent with real call_sid
                    if call_sid and call_sid != temp_call_sid:
                        agent.call_sid = call_sid
                        active_sessions[call_sid] = agent
                        if temp_call_sid in active_sessions:
                            del active_sessions[temp_call_sid]
                    
                elif event_type == "media":
                    media_data = data.get("media", {})
                    track = media_data.get("track", "unknown")
                    payload_length = len(media_data.get("payload", ""))
                    
                    logger.info(f"[DEBUG] 🎵 Media packet: track={track}, size={payload_length}")
                    await agent.handle_incoming_audio(media_data)
                    
                elif event_type == "stop":
                    logger.info(f"[DEBUG] 🛑 Stream stopped")
                    break
                    
                else:
                    logger.info(f"[DEBUG] ❓ Unknown event: {event_type}")
                    logger.info(f"[DEBUG] Full data: {data}")
                    
            except json.JSONDecodeError as e:
                logger.error(f"[DEBUG] ❌ JSON decode error: {e}")
            except Exception as e:
                logger.error(f"[DEBUG] ❌ Message processing error: {e}")
                
    except WebSocketDisconnect:
        logger.info(f"[DEBUG] 🔌 WebSocket disconnected after {message_count} messages")
    except Exception as e:
        logger.error(f"[DEBUG] ❌ WebSocket fatal error: {e}")
        logger.error(traceback.format_exc())
    finally:
        logger.info(f"[DEBUG] 🧹 Cleanup for call")
        if agent:
            await agent.stop()
        # Clean up both possible call_sids
        for sid in [call_sid, temp_call_sid]:
            if sid and sid in active_sessions:
                del active_sessions[sid]


@app.get("/test-ws")
async def test_websocket():
    return {"message": "WebSocket endpoint is reachable", "domain": config.PUBLIC_DOMAIN}

@app.get("/active-calls")
async def get_active_calls():
    return {"active_calls": list(active_sessions.keys()), "count": len(active_sessions)}

@app.post("/hangup-call/{call_sid}")
async def hangup_call(call_sid: str):
    try:
        call = twilio_client.calls(call_sid).update(status='completed')
        if call_sid in active_sessions:
            agent = active_sessions[call_sid]
            await agent.stop()
            del active_sessions[call_sid]
        logger.info(f"[DEBUG] Hung up call: {call_sid}")
        return {"success": True, "call_sid": call_sid, "status": "hung_up"}
    except Exception as e:
        logger.error(f"[DEBUG] Error hanging up call {call_sid}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to hang up call: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("PORT in config is", config.PORT)
    print("HOST in config is", config.HOST)
    uvicorn.run(app, host=config.HOST, port=config.PORT)
