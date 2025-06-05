import asyncio
import random
import string
import re
import time
from urllib.parse import urlparse, parse_qs
import httpx
import cloudscraper
from colorama import init, Fore, Back, Style
from datetime import datetime

from fake_useragent import UserAgent

# Initialize colorama for Windows color support
init(autoreset=True)

API_BASE = "https://api.mail.tm"
TRUMP_WALLET_API = "https://waitlist.slingshot.app/oncallsendsigninlink"
FIREBASE_API = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithEmailLink"
FIREBASE_KEY = "AIzaSyBEW0wf2eMgWZF7atPQeGugZMy8ohqpsfY"

PROXY_CONFIG = {
    "http": None,  # http://log:pass@ip:port
    "https": None  # http://log:pass@ip:port
}

ua = UserAgent()


def print_header():
    print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.BLACK}{Back.BLUE} TRUMP WALLET АВТОРЕГИСТРАЦИЯ {Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{Style.BRIGHT}>>> ИСТОЧНИК: t.me/c_c_cc_c_c <<<{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")


def log_info(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Fore.BLUE}[{timestamp}]{Style.RESET_ALL} {Fore.WHITE}{message}{Style.RESET_ALL}")


def log_success(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Fore.GREEN}[{timestamp}] [OK]{Style.RESET_ALL} {Fore.GREEN}{message}{Style.RESET_ALL}")


def log_error(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Fore.RED}[{timestamp}] [ОШИБКА]{Style.RESET_ALL} {Fore.RED}{message}{Style.RESET_ALL}")


def log_warning(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Fore.YELLOW}[{timestamp}] [ВНИМАНИЕ]{Style.RESET_ALL} {Fore.YELLOW}{message}{Style.RESET_ALL}")


def log_data(label, value):
    print(f"{Fore.CYAN}{label}:{Style.RESET_ALL} {Fore.WHITE}{value}{Style.RESET_ALL}")


def generate_random_string(length=10, chars=string.ascii_lowercase + string.digits):
    return "".join(random.choice(chars) for _ in range(length))


def generate_phone_number():
    area_code = random.randint(200, 999)
    prefix = random.randint(200, 999)
    line_number = random.randint(1000, 9999)
    return f"+1{area_code}{prefix}{line_number}"


def generate_twitter_username():
    username = generate_random_string(8, string.ascii_lowercase)
    return f"@{username}"


def generate_device_fingerprint():
    return ''.join(random.choice('0123456789abcdef') for _ in range(32))


def generate_ip_hash():
    return ''.join(random.choice('0123456789abcdef') for _ in range(16))


def create_trump_session():
    scraper = cloudscraper.create_scraper()

    user_agent = ua.random

    chrome_version = random.choice(["137", "138", "139", "140", "141"])

    languages = [
        "en-US,en;q=0.9",
        "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "en-GB,en;q=0.9,en-US;q=0.8",
        "es-ES,es;q=0.9,en;q=0.8",
        "fr-FR,fr;q=0.9,en;q=0.8"
    ]

    scraper.headers.update({
        'accept': '*/*',
        'accept-language': random.choice(languages),
        'origin': 'https://trumpwallet.com',
        'referer': 'https://trumpwallet.com/',
        'sec-ch-ua': f'"Chromium";v="{chrome_version}", "Google Chrome";v="{chrome_version}", "Not?A_Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'user-agent': user_agent,
    })

    scraper.cookies.update({
        'sessionId': generate_random_string(32, string.ascii_letters + string.digits),
        'deviceId': generate_device_fingerprint(),
    })

    if PROXY_CONFIG["http"] or PROXY_CONFIG["https"]:
        proxy = {k: v for k, v in PROXY_CONFIG.items() if v}
        scraper.proxies.update(proxy)

    return scraper


async def create_email_account(client: httpx.AsyncClient):
    log_info("Получение доступных доменов...")
    r = await client.get(f"{API_BASE}/domains")
    r.raise_for_status()
    domains = [d["domain"] for d in r.json().get("hydra:member", [])]
    if not domains:
        raise RuntimeError("Не удалось получить домены.")

    domain = random.choice(domains)

    local = generate_random_string(10)
    email = f"{local}@{domain}"
    password = generate_random_string(12, string.ascii_letters + string.digits)

    payload = {"address": email, "password": password}
    log_info("Создание email аккаунта...")
    r = await client.post(f"{API_BASE}/accounts", json=payload)
    r.raise_for_status()

    log_success(f"Email создан: {Fore.CYAN}{email}{Fore.GREEN}")
    return email, password


async def get_email_token(client: httpx.AsyncClient, email: str, password: str):
    payload = {"address": email, "password": password}
    r = await client.post(f"{API_BASE}/token", json=payload)
    r.raise_for_status()
    return r.json()["token"]


async def wait_for_trump_email(client: httpx.AsyncClient, jwt_token: str, timeout=120):
    headers = {"Authorization": f"Bearer {jwt_token}"}

    log_info("Ожидание письма от Trump Wallet...")
    start_time = time.time()
    dots = 0

    while time.time() - start_time < timeout:
        r = await client.get(f"{API_BASE}/messages", headers=headers)
        r.raise_for_status()
        msgs = r.json().get("hydra:member", [])

        for msg in msgs:
            mid = msg["id"]
            r2 = await client.get(f"{API_BASE}/messages/{mid}", headers=headers)
            r2.raise_for_status()
            data = r2.json()

            if "trump" in data.get("subject", "").lower() or "trump" in data.get("from", {}).get("address", "").lower():
                log_success(f"Письмо получено: {data.get('subject', 'Без темы')}")

                html_content = data.get("html", "")
                if isinstance(html_content, list):
                    html_content = " ".join(str(item) for item in html_content)
                pattern = r'https://email\.tx\.trumpwallet\.com/[^\s"\'<>]+'
                matches = re.findall(pattern, html_content)

                if matches:
                    return matches[0]
                else:
                    text_content = data.get("text", "")
                    if isinstance(text_content, list):
                        text_content = " ".join(str(item) for item in text_content)
                    matches = re.findall(pattern, text_content)
                    if matches:
                        return matches[0]

        # Animated waiting indicator
        dots = (dots + 1) % 4
        print(f"\r{Fore.YELLOW}Проверка почты{'.' * dots}{' ' * (3 - dots)}{Style.RESET_ALL}", end='', flush=True)
        await asyncio.sleep(3)

    print()  # New line after waiting
    raise TimeoutError("Не удалось получить письмо в течение заданного времени")


def extract_referral_code(referral_link):
    parsed = urlparse(referral_link)
    params = parse_qs(parsed.query)
    referral_code = params.get('ref', [None])[0]
    if not referral_code:
        raise ValueError("Не удалось извлечь referral code из ссылки")
    return referral_code


def register_trump_wallet(scraper, email: str, phone: str, twitter: str, referrer_id: str):
    headers = {
        'content-type': 'application/json',
        'priority': 'u=1, i',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
    }

    json_data = {
        'data': {
            'deviceFingerprint': generate_device_fingerprint(),
            'ipHash': generate_ip_hash(),
            'phoneNumber': phone,
            'usernameX': twitter,
            'referrerId': referrer_id,
            'email': email,
            'url': 'https://trumpwallet.com',
            'returningUser': False,
        },
    }

    log_info("Отправка запроса на регистрацию...")
    response = scraper.post(TRUMP_WALLET_API, headers=headers, json=json_data)
    response.raise_for_status()

    log_success(f"Регистрация отправлена для {Fore.CYAN}{email}{Fore.GREEN}")
    return response.json() if response.text else {}


def get_final_url_with_cloudscraper(scraper, url: str):
    log_info("Обработка ссылки из письма...")

    response = scraper.get(url, allow_redirects=True)

    final_url = response.url
    return final_url


def extract_oob_code(url: str):
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    oob_code = params.get('oobCode', [None])[0]
    if not oob_code:
        raise ValueError("Не удалось извлечь oobCode из URL")

    return oob_code


def complete_signin(scraper: cloudscraper.CloudScraper, email: str, oob_code: str):
    log_info("Выполнение Firebase аутентификации...")

    params = {'key': FIREBASE_KEY}
    payload = {
        'email': email,
        'oobCode': oob_code,
    }

    response = scraper.post(FIREBASE_API, params=params, json=payload)
    response.raise_for_status()
    auth_data = response.json()
    log_success("Firebase аутентификация успешна")
    log_data("ID Token", f"{auth_data['idToken'][:50]}...")

    slingshot_headers = {
        'accept': '*/*',
        'authorization': f"Bearer {auth_data['idToken']}",
        'content-type': 'application/json',
        'origin': 'https://trumpwallet.com',
        'referer': 'https://trumpwallet.com/',
        'user-agent': scraper.headers['User-Agent'],
    }

    log_info("Завершение авторизации...")
    response2 = scraper.post(
        'https://waitlist.slingshot.app/oncallgetdashboard',
        headers=slingshot_headers,
        json={'data': None}
    )
    response2.raise_for_status()
    log_success("Авторизация полностью завершена!")

    dashboard_data = response2.json()
    if 'data' in dashboard_data:
        log_data("Позиция в очереди", dashboard_data.get('data', {}).get('position', 'Н/Д'))

    return auth_data


async def create_single_account(trump_session, email_client, referrer_id):
    try:
        email, password = await create_email_account(email_client)

        jwt_token = await get_email_token(email_client, email, password)

        phone = generate_phone_number()
        twitter = generate_twitter_username()

        print(f"\n{Fore.CYAN}{'─' * 40}{Style.RESET_ALL}")
        log_data("Телефон", phone)
        log_data("Twitter", twitter)
        print(f"{Fore.CYAN}{'─' * 40}{Style.RESET_ALL}\n")

        register_trump_wallet(trump_session, email, phone, twitter, referrer_id)

        email_link = await wait_for_trump_email(email_client, jwt_token)
        log_success(f"Ссылка из письма получена")

        final_url = get_final_url_with_cloudscraper(trump_session, email_link)

        oob_code = extract_oob_code(final_url)

        auth_result = complete_signin(trump_session, email, oob_code)

        print(f"\n{Fore.GREEN}{'=' * 60}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}{Back.GREEN} РЕГИСТРАЦИЯ УСПЕШНО ЗАВЕРШЕНА! {Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'=' * 60}{Style.RESET_ALL}")

        print(f"\n{Fore.CYAN}Данные аккаунта:{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Email: {Fore.CYAN}{email}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Пароль от почты: {Fore.CYAN}{password}{Style.RESET_ALL}")

        with open("trump_wallet_accounts.txt", "a", encoding="utf-8") as f:
            f.write(f"\n{'=' * 50}\n")
            f.write(f"Дата: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Email: {email}\n")
            f.write(f"Пароль от почты: {password}\n")
            f.write(f"Телефон: {phone}\n")
            f.write(f"Twitter: {twitter}\n")

        log_success("Данные сохранены в trump_wallet_accounts.txt")

    except Exception as e:
        log_error(f"Произошла ошибка: {e}")
        raise


async def main():
    print_header()

    # Prompt user for the number of accounts
    try:
        num_accounts = int(input(f"{Fore.YELLOW}Сколько аккаунтов создать? (Введите число): {Style.RESET_ALL}"))
        if num_accounts <= 0:
            log_error("Число аккаунтов должно быть больше 0.")
            return
    except ValueError:
        log_error("Пожалуйста, введите корректное число.")
        return

    log_info(f"Будет создано {num_accounts} аккаунтов.")

    if PROXY_CONFIG["http"] or PROXY_CONFIG["https"]:
        log_warning(f"Используется прокси: {PROXY_CONFIG}")

    trump_session = create_trump_session()
    log_info(f"Сессия создана с User-Agent: {trump_session.headers['user-agent'][:50]}...")

    # Read referral link from ref.txt
    try:
        with open("ref.txt", "r", encoding="utf-8") as f:
            referral_link = f.read().strip()
        log_info(f"Referral link from ref.txt: {referral_link}")
    except FileNotFoundError:
        log_error("Файл ref.txt не найден. Убедитесь, что файл существует.")
        return

    # Extract referral code from the link
    try:
        referrer_id = extract_referral_code(referral_link)
        log_success(f"Referral code extracted: {referrer_id}")
    except ValueError as e:
        log_error(str(e))
        return

    async with httpx.AsyncClient(timeout=30) as email_client:
        for i in range(num_accounts):
            log_info(f"Создание аккаунта {i+1} из {num_accounts}...")
            await create_single_account(trump_session, email_client, referrer_id)
            if i < num_accounts - 1:
                log_info("Ожидание перед созданием следующего аккаунта...")
                await asyncio.sleep(5)  # Small delay between accounts to avoid rate limiting

    trump_session.close()

    print(f"\n{Fore.YELLOW}{Style.BRIGHT}{'─' * 60}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{Style.BRIGHT}>>> ИСТОЧНИК: t.me/c_c_cc_c_c <<<{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{Style.BRIGHT}{'─' * 60}{Style.RESET_ALL}")


if __name__ == "__main__":
    asyncio.run(main())