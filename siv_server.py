from fastapi import FastAPI, File, UploadFile, HTTPException
import pandas as pd
from io import StringIO
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from collections import defaultdict
import socket
from pydantic import BaseModel

app = FastAPI()
security = HTTPBasic()

class Item(BaseModel):
    my_msg: str

origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/trigger/")
async def trigger_pico(item: Item):
    received_msg = item.my_msg
    
    print(f"Received message: {received_msg}")
    
    # Connection configuration
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Enable SO_REUSEADDR option
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    server.bind(('localhost', 8089))
    server.listen(1)
    
    reponse_str = ''
    conn, addr = server.accept()
    conn.sendall(received_msg.encode('utf-8'))
    
    while True:
        conn, addr = server.accept()
        cmnd = conn.recv(4)  # The default size of the command packet is 4 bytes
        print(cmnd)
        
        if 'PASS' in str(cmnd):
            # Do the initialization action
            reponse_str = 'PASSED'
            conn.sendall(b'PASSED')
            
        elif 'FAIL' in str(cmnd):
            # Do the play action
            reponse_str = 'FAILED'
            conn.sendall(b'FAILED')
            
        elif 'QUIT' in str(cmnd):
            # Do the quiting action
            conn.sendall(b'MSG_SENT')
            break

    server.close()


    # Send the data back
    return {
        "response": reponse_str
    }


@app.post("/upload-csv/")
async def upload_csv(file: UploadFile = File(...)):
    # Reset the file pointer to the beginning of the file in case it's not at the start
    await file.seek(0)
    
    # Read the contents of the uploaded CSV file
    contents = await file.read()
    string_io = StringIO(contents.decode("utf-8"))

    print(f"Filename: {file.filename}")

    # Attempt to parse the contents using Pandas
    try:
        df = pd.read_csv(string_io)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse CSV: {e}")

    # Check for the required columns in the CSV
    if 'engine_id' not in df.columns or 'message_id' not in df.columns:
        raise HTTPException(status_code=422, detail="CSV missing required columns 'engine_id' or 'message_ids'")

    # Create a default dictionary to hold the engine_ids as keys and a list of message_ids as values
    engine_messages = defaultdict(list)

    # Iterate through the dataframe rows and populate the dictionary
    for _, row in df.iterrows():
        engine_messages[row['engine_id']].append(row['message_id'])

    # Convert the defaultdict to the desired list of dictionaries format
    result = [{"engine_id": engine_id, "message_ids": message_ids} for engine_id, message_ids in engine_messages.items()]


    # Send the data back
    return {
        "header": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "response": result
    }
