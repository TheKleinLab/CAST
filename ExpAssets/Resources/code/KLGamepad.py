import re
import sdl2

from klibs.KLResponseCollectors import ResponseListener, Response

# NOTE: If this is ever used for collecting joystick data, would need to implement
# threshold and deadzone to avoid useless oversensitive changes at rest

TRIGGER_LEFT = sdl2.SDL_CONTROLLER_AXIS_TRIGGERLEFT
TRIGGER_RIGHT = sdl2.SDL_CONTROLLER_AXIS_TRIGGERRIGHT
TRIGGER_AXES = (TRIGGER_LEFT, TRIGGER_RIGHT)
TRIGGER_MAX = 32767


class TriggerData(object):

    def __init__(self, t, lt=0, rt=0):
        self._time = t
        self._lt = lt
        self._rt = rt

    @property
    def timestamp(self):
        """float: The timestamp for the trigger movement.
        
        Relative to the onset of the response collection loop.
        
        """
        return self.time

    @property
    def left(self):
        """float: The state of the left trigger (min = 0.0, max = 1.0)."""
        return self._lt / TRIGGER_MAX

    @property
    def right(self):
        """float: The state of the right trigger (min = 0.0, max = 1.0)."""
        return self._rt / TRIGGER_MAX



class GamepadResponse(ResponseListener):

    def __init__(self, mapping=None):
        # Fallback mapping for missing controller?
        super(GamepadResponse, self).__init__("gamepad_listener")
        self._button_state = {}
        self._axis_state = {}
        self._map = {}
        self._user_map = {}
        self.pad = None
        self.record_triggers = False
        self._raw_trigger_data = []
        if mapping:
            self._map = self._parse_mappings(mapping)
            self._user_map = mapping

    def _get_axis(self, name_raw):
        name = re.sub(r"[\s_-]", "", name_raw).lower()
        axis = sdl2.SDL_GameControllerGetAxisFromString(name.encode('utf-8'))
        if axis == sdl2.SDL_CONTROLLER_AXIS_INVALID:
            print(name)
            raise ValueError("Invalid axis name '{0}'.".format(name_raw))
        return axis

    def _get_button(self, name_raw):
        name = re.sub(r"[\s_-]", "", name_raw).lower()
        b = sdl2.SDL_GameControllerGetButtonFromString(name.encode('utf-8'))
        if b == sdl2.SDL_CONTROLLER_BUTTON_INVALID:
            raise ValueError("Invalid button name '{0}'.".format(name_raw))
        return b

    def _parse_mappings(self, _map):
        out = {}
        for label, mapping in _map.items():
            buttons = []
            axes = []
            if isinstance(mapping, dict):
                mapping = [{k: v} for k, v in mapping.items()]
            elif isinstance(mapping, str):
                mapping = [mapping]
            for item in mapping:
                if isinstance(item, dict):
                    name, threshold = list(item.items())[0]
                    axis_map = (self._get_axis(name), int(threshold * 32767))
                    axes.append(axis_map)
                else:
                    buttons.append(self._get_button(item))
            out[label] = {'buttons': buttons, 'axes': axes}
        return out

    def _reset_state(self):
        self._button_state = {}
        self._axis_state = {}
        self._raw_trigger_data = []
        for mapping in self._map.values():
            for b in mapping['buttons']:
                self._button_state[b] = 0
            for axis, threshold in mapping['axes']:
                self._axis_state[axis] = 0

    def init(self):
        """See :meth:`ResponseListener.init`.

        """
        if self.pad:
            self.pad.update()
        self._reset_state()
        if not len(self._map):
            raise RuntimeError("No response map configured for the gamepad.")

    def listen(self, event_queue):
        """See :meth:`ResponseListener.listen`.

        """
        trigger_update = False
        for e in event_queue:
            if e.type == sdl2.SDL_CONTROLLERBUTTONDOWN:
                self._button_state[e.cbutton.button] = e.cbutton.state
            elif e.type == sdl2.SDL_CONTROLLERBUTTONUP:
                self._button_state[e.cbutton.button] = e.cbutton.state
            elif e.type == sdl2.SDL_CONTROLLERAXISMOTION:
                self._axis_state[e.caxis.axis] = e.caxis.value
                if e.caxis.axis in TRIGGER_AXES:
                    trigger_update = True

        if trigger_update:
            dat = TriggerData(
                t = (self.evm.trial_time_ms - self._rc_start),
                lt = self._axis_state[TRIGGER_LEFT],
                rt = self._axis_state[TRIGGER_RIGHT]
            )
            self._raw_trigger_data.append(dat)

        for label, mapping in self._map.items():
            incomplete = False
            for b in mapping['buttons']:
                pressed = self._button_state[b]
                if not pressed:
                    incomplete = True
                    break
            if incomplete:
                continue
            for axis, threshold in mapping['axes']:
                value = self._axis_state[axis]
                if threshold < 0:
                    valid = value <= threshold
                else:
                    valid = value >= threshold
                if not valid:
                    incomplete = True
                    break
            if not incomplete:
                rt = (self.evm.trial_time_ms - self._rc_start)
                return Response(label, rt)

        if self.pad:
            self.pad.update()

    @property
    def trigger_data(self):
        return self._raw_trigger_data

    @property
    def response_map(self):
        return self._user_map

    @response_map.setter
    def response_map(self, _map):
        self._map = self._parse_mappings(_map)
        self._user_map = _map

