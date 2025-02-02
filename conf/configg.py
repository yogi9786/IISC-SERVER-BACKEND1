import os
from dotenv import load_dotenv


load_dotenv()

CLIENT_ID = os.environ.get('474230928320-d76ijvbhg1pqulgi8gngo9278rrct960.apps.googleusercontent.com', None)
CLIENT_SECRET = os.environ.get('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', None)