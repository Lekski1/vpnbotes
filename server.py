import socket
import logging
import os

from subprocess import run
import traceback
from urllib.parse import quote
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime, timedelta

#region Настройка системы прологирования
logs_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
if not os.path.exists(logs_directory):
    os.makedirs(logs_directory)

LOGS_FILE = f'{logs_directory}/server_{datetime.now().strftime("%d_%m_%y")}.log'

logging.basicConfig(filename=LOGS_FILE, level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# Создание объекта логгера для данной функции
logger = logging.getLogger(__name__)

try:
    # Получение текущей даты и вычитание 5 дней
    current_date = datetime.now()
    days_to_subtract = 5
    date_threshold = current_date - timedelta(days=days_to_subtract)

    # Перебор файлов в директории logs
    for filename in os.listdir(logs_directory):
        file_path = os.path.join(logs_directory, filename)
        
        # Проверка времени создания файла
        if os.path.isfile(file_path):
            creation_time = datetime.fromtimestamp(os.path.getctime(file_path))
            if creation_time < date_threshold:
                os.remove(file_path)
except Exception as e:
    print(f'🛑Не удалось установить логгер: {e}')
#endregion

TEST = 'aleksandr' in socket.gethostname().lower()

if not TEST:
    # result = run('pip install flask==2.3.1 flask-httpauth==4.8.0 --break-system-packages', shell = True, capture_output = True, encoding='cp866')
    # result = result.stdout + '\n\n' + result.stderr
    # if 'no such option' in result:
    result = run('pipx install flask==2.3.1 flask-httpauth==4.8.0', shell = True, capture_output = True, encoding='cp866')
    result = result.stdout + '\n\n' + result.stderr
    logger.debug(result)

from flask import Flask, jsonify, make_response, request, redirect
from flask_httpauth import HTTPBasicAuth

app = Flask(__name__)
auth = HTTPBasicAuth()

def sendResult(success=True, data='', error=''):
    return {'success':success, 'data':data, 'error': error}

@auth.verify_password
def verify_password(username, password):
    try:
        if TEST:
            return True
        
        logger.debug(f'🔄Запрос авторизации: username: "{username}", password: "{password}"')

        if username != '__login__':
            logger.warning(f'❌Неверный логин: "{username}"')
            return False

        pass_res = ''.join([char.lower() for i, char in enumerate(password) if (i+1) % 2 == 0]) == '__password__'
        if not pass_res:
            logger.warning(f'❌Неверный пароль: "{password}"')
        else:
            logger.info(f'✅Пароль верный: "{password}"')
        return pass_res
    except Exception as e:
        logger.warning(f'❌Ошибка: {e}')
        return False

@auth.error_handler
def unauthorized():
    try:
        logger.warning(f'❌Ошибка авторизации')
        result = sendResult(success=False, error='Unauthorized access')
        return make_response(jsonify(result), 401)
    except Exception as e:
        logger.warning(f'❌Ошибка: {e}')
        return make_response(jsonify({'error': 'Unauthorized access'}), 401)

@app.errorhandler(404)
def not_found(error):
    try:
        logger.warning(f'❌Ошибка 404: {error}')
        result = sendResult(success=False, error=f'Not found: {error}')
        return make_response(jsonify(result), 404)
    except Exception as e:
        logger.warning(f'❌Ошибка: {e}')
        return make_response(jsonify({'error': 'Not found'}), 404)

@app.route('/v', methods=['GET'])
def redirect_to_link():
    c = request.args.get('c')
    security = request.args.get('security')
    fp = request.args.get('fp')
    pbk = request.args.get('pbk')
    sni = request.args.get('sni')
    sid = request.args.get('sid')
    name = request.args.get('name')
    link = f'{c}&security={security}&fp={fp}&pbk={pbk}&sni={sni}&sid={sid}&spx=%2F#{name}'
    return redirect(link)

@app.route('/pay', methods=['GET'])
def redirect_to_pay():
    html = '''
<!DOCTYPE html><html>
<head>
<meta charset="UTF-8">
<base href="/">
<style>
html {
    height: 100vh;
}

body {
    height: 100%;
    position: fixed;
}
</style>
</head>
<body>
<script>
window.onload = function() {
    var params = new URLSearchParams(window.location.search);
    var url = params.get('url');
    window.location.href = url;
};
</script>
</body>
</html>'''
    return html

@app.route('/red', methods=['GET'])
def redirect_to_link_out_ss():
    html = '''
<!DOCTYPE html><html>
<head>
<meta charset="UTF-8">
</head>
<body>
<script>
window.onload = function() {
    var params = new URLSearchParams(window.location.search);
    var key = params.get('url');
    var name = params.get('name');
    var redirectUrl = "ss://" + key + "#" + name;
    window.location.href = redirectUrl;
};
</script>
</body>
</html>'''
    return html

@app.route('/red_vl', methods=['GET'])
def redirect_key():
    html = '''
<!DOCTYPE html><html><head><meta charset="UTF-8"></head><body><script>
window.onload = function() {
    var params = new URLSearchParams(window.location.search);
    var key = params.get('url');
    var name = params.get('name');

    for (var i = 0; i < 10; i++) {
        key = key.replace('a_n_d', '&');
    }

    var redirectUrl = key + '#' + name;
    window.location.href = redirectUrl;
};
</script></body></html>'''
    return html

@app.route('/', methods=['POST'])
@auth.login_required
def server():
    try:
        #region Получение параметров из тела POST-запроса
        params = request.json
        command = ''
        path = ''
        logger.debug(f'🔄Полученные параметры: {params}')

        if not 'command' in params and not 'path' in params:
            logger.warning(f'❌Нет команды и пути')
            result = sendResult(success=False, error='No command and path')
            return jsonify(result), 404

        if 'command' in params and params['command'] == '' and 'path' in params and params['path'] == '':
            logger.warning(f'❌Пустая команда и путь')
            result = sendResult(success=False, error='Empty command and path')
            return jsonify(result), 404

        if 'command' in params:
            command = params['command']
        if 'path' in params:
            path = params['path']

        logger.debug(f'🔄Запрос: command: "{command}", path: "{path}"')
        #endregion

        if command != '':
            logger.warning(f'🔄Выполняем команду: "{command}"')
            result = run(command, shell = True, capture_output = True, encoding='cp866')
            res = ''
            if result.stdout and result.stdout != '':
                res += result.stdout
            if result.stderr and result.stderr != '':
                res += '\n\n' + result.stderr
            if path == '':
                logger.debug(f'✅Результат выполнения команды ({command}): {res}')
                result = sendResult(data=res)
                return jsonify(result), 201
            
        if path != '':
            with open(path,'r') as file:
                data = file.read()
                logger.debug(f'📄Прочитанный файл: {data}')
                result = sendResult(data=data)
                return jsonify(result), 201
    except Exception as e:
        logger.warning(f'❌Ошибка: {traceback.format_exc(limit=1, chain=False)}')
        result = sendResult(success=False, error=f'Error: {e}')
        return jsonify(result), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=43234, debug=True, use_reloader=False)
