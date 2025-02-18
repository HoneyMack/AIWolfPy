import socket
import json
from aiwolfpy.gameinfoparser import GameInfoParser


# decorator / proxy
class AgentProxy(object):

    def __init__(self, agent, my_name, host_name, port, role, logger, parse="pandas", total_games=5,socket_timeout=300):
        self.agent = agent
        self.my_name = my_name
        self.host_name = host_name
        self.port = port
        self.role = role
        self.sock = None
        self.parser = GameInfoParser()
        self.base_info = dict()
        self.parse_choice = parse
        self.logger = logger
        self.len_whisper_list = 0
        self.total_games = total_games
        self.socket_timeout = socket_timeout
        self.game_start_count = 0
        self.game_end_count = 0

    # parse and run
    def initialize_agent(self, game_info, game_setting):
        if self.parse_choice == "pandas":
            self.parser.initialize(game_info, game_setting)
            self.base_info = dict()
            self.base_info['agentIdx'] = game_info['agent']
            self.base_info['myRole'] = game_info["roleMap"][str(game_info['agent'])]
            self.base_info["roleMap"] = game_info["roleMap"]
            diff_data = self.parser.get_game_df_diff()
            self.logger.debug("INITIALIZE")
            self.logger.debug(self.base_info)
            self.logger.debug(diff_data)
            self.agent.initialize(self.base_info,  diff_data, game_setting)
            return None
        else:
            self.agent.initialize(game_info, game_setting)

    # parse and run
    def update_agent(self, game_info, talk_history, whisper_history, request):
        if self.parse_choice == "pandas":
            for k in ["day", "remainTalkMap", "remainWhisperMap", "statusMap"]:
                if k in game_info.keys():
                    self.base_info[k] = game_info[k]
            self.parser.update(game_info, talk_history, whisper_history, request)
            diff_data = self.parser.get_game_df_diff()
            self.logger.debug(request)
            self.logger.debug(self.base_info)
            self.logger.debug(diff_data)
            self.agent.update(self.base_info, diff_data, request)
            return None
        else:
            self.agent.update(game_info, talk_history, whisper_history, request)

    def send_response(self, json_received):
        res_txt = self._get_json(json_received)
        if res_txt is None:
            pass
        else:
            self.sock.send((res_txt + '\n').encode('utf-8'))
        return None

    def _get_json(self, json_received):
        game_info = json_received['gameInfo']
        if game_info is None:
            game_info = dict()
        # talk_history and whisper_history
        talk_history = json_received['talkHistory']
        if talk_history is None:
            talk_history = []
        whisper_history = json_received['whisperHistory']
        if whisper_history is None:
            whisper_history = []

        # delete unnecessary talk and whisper
        if 'talkList' in game_info.keys():
            del game_info['talkList']
        if 'whisperList' in game_info.keys():
            whisper_history = game_info['whisperList'][self.len_whisper_list:]
            self.len_whisper_list = len(game_info['whisperList'])
            del game_info['whisperList']

        # request must exist
        request = json_received['request']
        self.logger.log(1, request)
        self.logger.log(1, game_info)
        self.logger.log(1, talk_history)
        self.logger.log(1, whisper_history)
        if request == 'INITIALIZE':
            game_setting = json_received['gameSetting']
            self.logger.log(1, game_setting)
            self.game_start_count += 1 #ゲームが始まったらカウントを増やす
        else:
            game_setting = None

        #print("request:", request)
        # run_request
        if request == 'NAME':
            return self.my_name
        elif request == 'ROLE':
            return self.role
        elif request == 'INITIALIZE':
            self.initialize_agent(game_info, game_setting)
            return None
        else:
            # UPDATE
            self.update_agent(game_info, talk_history, whisper_history, request)
            if request == 'DAILY_INITIALIZE':
                self.len_whisper_list = 0
                self.agent.dayStart()
                return None
            elif request == 'DAILY_FINISH':
                return None
            elif request == 'FINISH':
                self.agent.finish()
                if self.game_start_count -1 == self.game_end_count:
                    self.game_end_count += 1 #ゲームが終わったらカウントを増やす
                return None
            elif request == 'VOTE':
                return json.dumps({'agentIdx': int(self.agent.vote())}, separators=(',', ':'))
            elif request == 'ATTACK':
                return json.dumps({'agentIdx': int(self.agent.attack())}, separators=(',', ':'))
            elif request == 'GUARD':
                return json.dumps({'agentIdx': int(self.agent.guard())}, separators=(',', ':'))
            elif request == 'DIVINE':
                return json.dumps({'agentIdx': int(self.agent.divine())}, separators=(',', ':'))
            elif request == 'TALK':
                return self.agent.talk().__str__()
            elif request == 'WHISPER':
                return self.agent.whisper().__str__()

    def connect_server(self):
        # socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.socket_timeout)
        # connect
        self.sock.connect((self.host_name, self.port))
        
        while self.game_end_count < self.total_games:
            response = self.receive()
            if response == "":
                break
        
            line_list = response.split("\n")
            for one_line in line_list:
                if len(one_line) > 0:
                    json_received = json.loads(one_line)
                    self.send_response(json_received)

        self.sock.close()
                
        return None

    def is_json_complate(self,responses:bytes) -> bool:
        try:
            responses = responses.decode("utf-8")
        except:
            return False
        
        if responses == "":
            return False

        cnt = 0

        for word in responses:
            if word == "{":
                cnt += 1
            elif word == "}":
                cnt -= 1
        
        return cnt == 0
    
    def receive(self) -> str:
        responses = b""
        retry_count = 0
        max_retry_count = 1e5
        while not self.is_json_complate(responses=responses):  
            response = self.sock.recv(8192)
            #待機時間が長いときは、一定回数以上のリトライを許容する        
            if response == b"":
                retry_count += 1
                if retry_count > max_retry_count:
                    raise RuntimeError("socket connection broken")
            else:
                retry_count = 0
            
            responses += response

        return responses.decode("utf-8")