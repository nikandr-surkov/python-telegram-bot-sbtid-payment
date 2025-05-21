"""
Tung Tung Tung Sahur NFT Bot

This Telegram bot facilitates the purchase and verification of Social Bound Identity Tokens (SBTID)
on the TON blockchain. It allows users to purchase NFTs tied to their Telegram IDs through
a web application interface and verify their purchases directly through the bot.

The bot interacts with a TON smart contract to check if users have minted NFTs associated
with their Telegram IDs, providing a seamless experience without requiring database storage.

## Author
### Nikandr Surkov
- 🌐 Website: https://nikandr.com
- 📺 YouTube: https://www.youtube.com/@NikandrSurkov
- 📱 Telegram: https://t.me/nikandr_s
- 📢 Telegram Channel: https://t.me/+hL2jdmRkhf9jZjQy
- 📰 Clicker Game News: https://t.me/clicker_game_news
- 💻 GitHub: https://github.com/nikandr-surkov
- 🐦 Twitter: https://x.com/NikandrSurkov
- 💼 LinkedIn: https://www.linkedin.com/in/nikandr-surkov/
- ✍️ Medium: https://medium.com/@NikandrSurkov

Project Repository: https://github.com/nikandr-surkov/python-telegram-bot-sbtid-payment
"""

import sys
import os
import logging
import hashlib
import hmac
import json
import urllib.parse
import base64
import asyncio
from typing import Dict, Any, Optional, Union, List, Tuple, TypedDict, cast

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
import aiohttp

# Import for TON address parsing
try:
    from pytoniq_core import Cell, Address
except ImportError:
    logging.error("pytoniq_core is not installed. Please install it using: pip install pytoniq-core")
    raise

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   handlers=[logging.StreamHandler(stream=sys.stdout)])
logger = logging.getLogger(__name__)

"""
Required Environment Variables:

BOT_TOKEN: Telegram Bot API token obtained from BotFather
    Format: "1234567890:AAHHsample_token_textsampletoken"

CONTRACT_ADDRESS: TON smart contract address for the NFT collection
    Format: "EQsomeaddresshere" (TON user-friendly address format)

QUICKNODE_ENDPOINT: API endpoint for TON blockchain interaction
    Format: "https://your-endpoint.quiknode.pro/api-key-here"
    Note: Must include the full URL with protocol and any API keys

Optional Environment Variables:

LOG_LEVEL: Sets the logging level (default: INFO)
    Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

CACHE_TIMEOUT: Time in seconds to cache blockchain seqno (default: 60)
    Format: Integer value, recommended range 30-300
"""
# Load environment variables
load_dotenv()

# Initialize bot and required components
BOT_TOKEN: Optional[str] = os.getenv("BOT_TOKEN")
CONTRACT_ADDRESS: Optional[str] = os.getenv("CONTRACT_ADDRESS")
QUICKNODE_ENDPOINT: Optional[str] = os.getenv("QUICKNODE_ENDPOINT")

# Validate required environment variables
if not all([BOT_TOKEN, CONTRACT_ADDRESS, QUICKNODE_ENDPOINT]):
    missing: List[str] = []
    if not BOT_TOKEN: missing.append("BOT_TOKEN")
    if not CONTRACT_ADDRESS: missing.append("CONTRACT_ADDRESS")
    if not QUICKNODE_ENDPOINT: missing.append("QUICKNODE_ENDPOINT")
    raise ValueError(f"Missing environment variables: {', '.join(missing)}")

# Initialize bot with default properties
bot: Bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=None))
storage: MemoryStorage = MemoryStorage()
dp: Dispatcher = Dispatcher(storage=storage)
router: Router = Router()

# Convert to non-Optional after validation
BOT_TOKEN = cast(str, BOT_TOKEN)
CONTRACT_ADDRESS = cast(str, CONTRACT_ADDRESS)
QUICKNODE_ENDPOINT = cast(str, QUICKNODE_ENDPOINT)

# Global HTTP session that will be used for all API requests
# This follows best practices by reusing the same session for all requests
http_session: Optional[aiohttp.ClientSession] = None


class SeqnoCache(TypedDict):
    value: int
    timestamp: float


# Cached seqno with timestamp to avoid too many requests
_seqno_cache: SeqnoCache = {"value": 0, "timestamp": 0}


class ValidationResult(TypedDict, total=False):
    isValid: bool
    userId: Optional[int]


async def get_session() -> aiohttp.ClientSession:
    """Get or create the global HTTP session."""
    global http_session
    if http_session is None or http_session.closed:
        http_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=10, force_close=False, enable_cleanup_closed=True)
        )
    return http_session


def validate_telegram_webapp_data(init_data: str) -> ValidationResult:
    """Validates the data received from Telegram WebApp"""
    try:
        parsed_data: Dict[str, str] = dict(urllib.parse.parse_qsl(init_data))
        received_hash: Optional[str] = parsed_data.pop('hash', None)

        if not received_hash:
            logger.warning("Hash missing in initData")
            return {"isValid": False}

        # Create data check string
        data_check_arr: List[str] = [f"{key}={parsed_data[key]}" for key in sorted(parsed_data.keys())]
        data_check_string: str = '\n'.join(data_check_arr)

        # Calculate hash
        secret_key: bytes = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash: str = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        if calculated_hash != received_hash:
            logger.warning(f"Hash mismatch: calculated {calculated_hash}, received {received_hash}")
            return {"isValid": False}

        # Extract user data
        user_data_str: Optional[str] = parsed_data.get('user')
        if not user_data_str:
            logger.warning("User data missing in initData")
            return {"isValid": False, "userId": None}

        user_data: Dict[str, Any] = json.loads(user_data_str)
        return {
            "isValid": True,
            "userId": user_data.get('id')
        }
    except Exception as e:
        logger.error(f"Error validating Telegram data: {e}", exc_info=True)
        return {"isValid": False}


async def check_nft_active(nft_address: str) -> bool:
    """Check if a TON smart contract at the given address is active"""
    endpoint_url: str = f"{QUICKNODE_ENDPOINT}/getAddressState"
    full_url: str = f"{endpoint_url}?address={nft_address}"

    try:
        session: aiohttp.ClientSession = await get_session()
        async with session.get(
                full_url,
                headers={"accept": "application/json"},
                raise_for_status=True
        ) as response:
            data: Dict[str, Any] = await response.json()

            if not data.get("ok", False):
                logger.warning(f"API error: {data.get('error', 'Unknown error')}")
                return False

            state: str = data.get("result", "")
            return state == "active"

    except aiohttp.ClientResponseError as e:
        logger.warning(f"Failed API call to getAddressState: {e.status}")
        return False
    except Exception as e:
        logger.error(f"Error checking if NFT is active: {e}", exc_info=True)
        return False


async def get_current_seqno() -> int:
    """Fetch the current sequence number (seqno) from the TON blockchain, with caching"""
    global _seqno_cache

    # Cache seqno for 1 minute to reduce API calls
    current_time: float = asyncio.get_event_loop().time()
    if current_time - _seqno_cache["timestamp"] < 60:  # 60 seconds cache
        return _seqno_cache["value"]

    try:
        masterchain_url: str = f"{QUICKNODE_ENDPOINT.rstrip('/')}/getMasterchainInfo"
        session: aiohttp.ClientSession = await get_session()

        async with session.get(
                masterchain_url,
                headers={"accept": "application/json"},
                raise_for_status=True
        ) as response:
            data: Dict[str, Any] = await response.json()

            if not data.get("ok", False):
                logger.warning(f"API error fetching masterchain info: {data.get('error', 'Unknown error')}")
                return _seqno_cache["value"] or 0  # Use cached value or 0

            # Extract the seqno from the last block
            result: Dict[str, Any] = data.get("result", {})
            last_block: Dict[str, Any] = result.get("last", {})
            seqno: int = last_block.get("seqno", 0)

            # Update cache
            _seqno_cache = {"value": seqno, "timestamp": current_time}
            logger.info(f"Current blockchain seqno: {seqno}")
            return seqno

    except aiohttp.ClientResponseError as e:
        logger.warning(f"Failed to get masterchain info: Status {e.status}")
        return _seqno_cache["value"] or 0  # Use cached value or 0
    except Exception as e:
        logger.exception(f"Error fetching current seqno: {e}")
        return _seqno_cache["value"] or 0  # Use cached value or 0


async def get_nft_address(user_id: int) -> str:
    """Get the NFT address for a user and verify if it's active"""
    try:
        # First, get the current seqno from the blockchain
        current_seqno: int = await get_current_seqno()
        rest_url: str = f"{QUICKNODE_ENDPOINT.rstrip('/')}/runGetMethod"

        # Prepare payload according to the documentation
        payload: Dict[str, Any] = {
            "address": CONTRACT_ADDRESS,
            "method": "get_nft_address_by_index",
            "stack": [["num", str(user_id)]],
            "seqno": current_seqno
        }

        session: aiohttp.ClientSession = await get_session()
        try:
            async with session.post(
                    rest_url,
                    json=payload,
                    headers={"Content-Type": "application/json", "accept": "application/json"},
                    raise_for_status=True
            ) as response:
                data: Dict[str, Any] = await response.json()
        except aiohttp.ClientResponseError as e:
            return f"Error communicating with blockchain: Status {e.status}"

        # Check if request was successful
        if not data.get("ok", False):
            error_msg: str = data.get("error", "Unknown error")
            return f"Blockchain error: {error_msg}"

        result: Optional[Dict[str, Any]] = data.get("result")
        if not result:
            return "Invalid response from blockchain"

        # Check exit code
        exit_code: Optional[int] = result.get("exit_code")
        if exit_code is not None and exit_code not in [0, -1, -14]:
            return f"ℹ️ NFT for user {user_id} is likely not minted (exit code: {exit_code})."

        if exit_code == -14:
            return f"ℹ️ NFT for user {user_id} is not minted (index not found in collection)."

        # Process stack result
        stack: Optional[List[Any]] = result.get("stack")
        if not stack or len(stack) == 0:
            return f"ℹ️ NFT for user {user_id} is not minted (empty stack)."

        # Get first stack item
        item_type: str
        item_value: Any
        item_type, item_value = stack[0]

        # Process cell data for address
        if item_type == "cell" and isinstance(item_value, dict) and "bytes" in item_value:
            cell_boc_b64: str = item_value["bytes"]
            try:
                # Decode and parse cell
                cell_bytes: bytes = base64.b64decode(cell_boc_b64)
                deserialized_cell: Cell = Cell.one_from_boc(cell_bytes)
                addr_slice = deserialized_cell.begin_parse()
                nft_addr_obj: Optional[Address] = addr_slice.load_address()

                if not nft_addr_obj or nft_addr_obj.hash_part == b'\x00' * 32:
                    return f"ℹ️ NFT for user {user_id} is not minted (zero address returned)."

                # Convert address to string format
                nft_address_str: str = nft_addr_obj.to_str(is_user_friendly=True, is_bounceable=True,
                                                      is_url_safe=True)

                # Check if NFT is active
                is_active: bool = await check_nft_active(nft_address_str)
                if is_active:
                    return f"✅ Minted NFT Address: {nft_address_str}"
                else:
                    return f"ℹ️ NFT for user {user_id} is not minted (address {nft_address_str} is not active)."

            except Exception as e:
                return f"⚠️ Error processing blockchain data: {str(e)}"

        elif item_type == "null" or (item_type == "num" and item_value == "0"):
            return f"ℹ️ NFT for user {user_id} is not minted (no address found)."
        else:
            return "Unexpected data format in blockchain response."

    except Exception as e:
        logger.exception(f"Error getting NFT address: {e}")
        return f"An unexpected error occurred: {str(e)}"


@router.message(Command("start"))
async def cmd_start(message: types.Message) -> None:
    """Handle /start command"""
    payment_url: str = f"https://sbtid.nikandr.com/collection?contract={CONTRACT_ADDRESS}&socialId={message.from_user.id}"
    keyboard: InlineKeyboardMarkup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🪵 Get Tung Tung Tung Sahur", web_app=WebAppInfo(url=payment_url))],
            [InlineKeyboardButton(text="🔍 Check Payment", callback_data="check_payment")]
        ]
    )
    await message.answer(
        "Welcome to the Tung Tung Tung Sahur Bot! 🪵\n\n"
        "Get your Tung Tung Tung Sahur by making a payment with TON blockchain:",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "check_payment")
async def check_payment_callback(callback: types.CallbackQuery) -> None:
    """Handle check payment button press"""
    await callback.answer()
    user_id: int = callback.from_user.id
    processing_message: types.Message = await callback.message.answer("⏳ Checking payment status, please wait...")

    try:
        result_message: str = await get_nft_address(user_id)
        await processing_message.edit_text(result_message)
    except Exception as e:
        logger.exception(f"Error checking payment: {e}")
        await processing_message.edit_text("⚠️ An unexpected error occurred. Please try again later.")


@router.message(F.web_app_data)
async def web_app_handler(message: types.Message) -> None:
    """Handle data received from web app"""
    web_app_data_str: str = message.web_app_data.data
    processing_message: types.Message = await message.answer("Processing web app data...")

    try:
        # Parse web app data
        parsed_data: Dict[str, Any] = json.loads(web_app_data_str)
        init_data: Optional[str] = parsed_data.get("initData")

        if not init_data:
            await processing_message.edit_text("Invalid web app data: Missing initData.")
            return

        # Validate web app data
        validation: ValidationResult = validate_telegram_webapp_data(init_data)
        if not validation.get("isValid"):
            await processing_message.edit_text("Authentication failed: Invalid data from web app.")
            return

        # Get user ID from validated data
        user_id: Optional[int] = validation.get("userId")
        if not user_id:
            await processing_message.edit_text("Authentication successful, but user ID missing.")
            return

        try:
            user_id = int(user_id)
        except ValueError:
            await processing_message.edit_text("Invalid user ID format from web app.")
            return

        # Check NFT status
        await processing_message.edit_text(f"Web app data validated. Checking NFT status...")
        result_message: str = await get_nft_address(user_id)
        await processing_message.edit_text(result_message)

    except json.JSONDecodeError:
        await processing_message.edit_text("Invalid data format received from web app.")
    except Exception as e:
        logger.exception(f"Error processing web app data: {e}")
        await processing_message.edit_text("An error occurred while processing your request.")


# Register router and start bot
dp.include_router(router)


async def on_startup() -> None:
    """Initialize resources when the bot starts"""
    global http_session
    http_session = await get_session()
    logger.info("Bot is starting...")


async def on_shutdown() -> None:
    """Clean up resources when the bot shuts down"""
    global http_session
    if http_session and not http_session.closed:
        await http_session.close()
        logger.info("HTTP session closed")


async def main() -> None:
    """Main function to run the bot"""
    try:
        # Set up the application
        await on_startup()

        # Start the bot
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        # Ensure resources are cleaned up
        await on_shutdown()


if __name__ == "__main__":
    try:
        logger.info("Starting Tung Tung Tung Sahur NFT Bot...")
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
    except Exception as e:
        logger.critical(f"Bot crashed: {e}", exc_info=True)