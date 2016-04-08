import re

RE_HEIMDALL = re.compile(
    b"""\\(<img src='fsh://system.fsh:86' /> You are connected to Heimdall \\[(\d+):(\d+)\\] \\(QTEMP (\d+)\\)\\. There are (\d+) players on this Heimdall, of which you are player index (\d+) with globalid (\d+), and you are on map (\d+)""")

RE_HORTON = re.compile(
    b"""\\(<img src='fsh://system.fsh:86' /> You are connected to Horton \\[(.*):(\d+)\\] \\(QTEMP (\d+)\\)\\. There are (\d+) players in this horton, of which you are the player index (\d+) with global id (\d+)\\. It's a beautiful day in Gosford Park. Horton is running version: (\w*)""")

RE_TRIBBLE = re.compile(
    b"""\\(<img src='fsh://system.fsh:86' /> You are connected to tribble \\[(\d+)\\] \\(QTEMP <b>(\d+)</b>\\)\\. There are (\d+) players on this tribble, of which you are player index (\d+) with global id (\d+)\\. You are exactly at \\((\d+),(\d+)\\)\\. This tribble feels like (.*) and is running version: (\w*)""")


class WhichStringParser(object):
    @staticmethod
    def try_handle(line, expression, success_callback=None):
        result = expression.findall(line)
        is_success = result != []

        # activate success_callback with the extracted expression data
        if is_success and success_callback:
            success_callback(
                tuple(map(
                    lambda d: int(d) if d.isdigit() else d.decode('utf-8'),
                    result[0])))

        # return if matched or not
        return is_success

    @staticmethod
    def parse_heimdall(data):
        (port, heimdall_id, qtemp, h_players, h_my_index, global_id, tribble_id) = data
        return {
            'type': 'heimdall',
            'id': heimdall_id,
            'port': port,
            'qtemp': qtemp,
            'num_players': h_players,
            'my': {
                'player_index': h_my_index,
                'global_id': global_id,
                'tribble_id': tribble_id
            }
        }

    @staticmethod
    def parse_horton(data):
        (h_addr, h_port, qtemp, num_players, my_player_index, my_global_id, version) = data
        return {
            'type': 'horton',
            'address': (h_addr, h_port),
            'qtemp': qtemp,
            'version': version,
            'num_players': num_players,
            'my': {
                'player_index': my_player_index,
                'global_id': my_global_id
            }
        }

    @staticmethod
    def parse_tribble(data):
        (tribble_id, qtemp, num_players, my_player_index, my_global_id, coord_x, coord_y, map_id, version) = data
        return {
            'type': 'tribble',
            'id': tribble_id,
            'qtemp': qtemp,
            'version': version,
            'map': map_id,
            'num_players': num_players,
            'my': {
                'player_index': my_player_index,
                'global_id': my_global_id,
                'coords': (coord_x, coord_y)
            }
        }

    @staticmethod
    def parse(line, callback=lambda data: None):
        handlers = {
            RE_HEIMDALL: WhichStringParser.parse_heimdall,
            RE_HORTON: WhichStringParser.parse_horton,
            RE_TRIBBLE: WhichStringParser.parse_tribble,
        }

        for expression in handlers.keys():
            parse_func = handlers[expression]
            if WhichStringParser.try_handle(line, expression, lambda data: callback(parse_func(data))):
                return True
        return False
