import asyncio
import httpx
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request, staticfiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import requests
import uvicorn
from fastapi.staticfiles import StaticFiles

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Metodo para cargar la imagen de fondo
app.mount("/static", StaticFiles(directory="static"), name="static")

# Get del root
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/auctions", response_class=HTMLResponse)
async def get_auction_data(request: Request):
    auction_data = []
    try:
        pages_data = await fetch_all_auction_data()
        for page_data in pages_data:
            if page_data:
                for item in page_data.get('auctions', []):
                    auction_data.append({
                        "playerUUID": item['auctioneer'],
                        "itemName": item['item_name'],
                        "price": format_number_with_commas(item['starting_bid']),
                        "timeLeft": convert_milliseconds_to_hours_minutes(item['end'])
                    })
    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return templates.TemplateResponse("auctions.html", {"request": request, "auction_data": auction_data})

# Cojer el numero de paginas del bazar para despues poder iterar por ellas
async def fetch_all_auction_data():
    async with httpx.AsyncClient() as session:
        response = await session.get("https://api.hypixel.net/skyblock/auctions")
        if response.status_code == 200:
            data = response.json()
            total_pages = data.get('totalPages', 0)
            tasks = [fetch_auction_page(session, page) for page in range(total_pages)]
            return await asyncio.gather(*tasks)
        else:
            print(f"Failed to fetch total pages. Status code: {response.status_code}")
            return []

# Cojer la informacion de la pagina en concreto
async def fetch_auction_page(session, page):
    try:
        url = f"https://api.hypixel.net/skyblock/auctions?page={page}"
        response = await session.get(url)
        
        if response.status_code == 200:
            return response.json()
        else:
            # print(f"Failed to fetch data from {url}. Status code: {response.status_code}")
            return None
    except httpx.RequestError as req_err:
        # print(f"Request error in fetch_auction_page for page {page}: {req_err}")
        return None
    except Exception as e:
        # print(f"An error occurred in fetch_auction_page for page {page}: {e}")
        return None

# Get para la informacion del bazaar
@app.get("/bazaar")
async def root(request: Request):
    response = requests.get("https://api.hypixel.net/skyblock/bazaar")
    
    if response.status_code == 200:
        data = response.json()
        
        items_info = []
        
        for item_name, item_data in data["products"].items():
            item_info = {
                "name": item_name,
                "min_price":format_number_with_commas(round(item_data["quick_status"]["sellPrice"])),
                "max_price":format_number_with_commas(round(item_data["quick_status"]["buyPrice"])),
                "avg_price":format_number_with_commas(round((item_data["quick_status"]["sellPrice"] + item_data["quick_status"]["buyPrice"]) / 2)),
                "quantity": format_number_with_commas(item_data["quick_status"]["buyMovingWeek"])
            }
            
            items_info.append(item_info)

        return templates.TemplateResponse("bazaar.html", {"request": request, "bazaar_data": items_info})
    else:
        return {"Error": "Failed to fetch data from the API"}

# Funciones de utilidad
def convert_milliseconds_to_hours_minutes(millis):
    seconds = millis / 1000.0
    remaining_time = timedelta(seconds=seconds)
    
    hours, remainder = divmod(remaining_time.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    time_left = f"{int(hours)}h {int(minutes)}m"
    return time_left
    
def format_number_with_commas(number):
    reversed_number_str = str(number)[::-1]
    
    formatted_number = ".".join([reversed_number_str[i:i+3] for i in range(0, len(reversed_number_str), 3)])
    
    formatted_number = formatted_number[::-1]
    
    return formatted_number

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
