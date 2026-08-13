import sdl2

from klibs.KLEventQueue import flush
from klibs.KLResponseListeners import BaseResponseListener

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
        return self._time

    @property
    def left(self):
        """float: The state of the left trigger (min = 0.0, max = 1.0)."""
        return self._lt / TRIGGER_MAX

    @property
    def right(self):
        """float: The state of the right trigger (min = 0.0, max = 1.0)."""
        return self._rt / TRIGGER_MAX



class TriggerListener(BaseResponseListener):
    """A class for collecting gamepad trigger responses.

    This response listener allows for three types of responses: left trigger,
    right trigger, and/or both triggers. Each of these can be mapped to a given response
    label::

       self.trig_listener = TriggerListener(
           {'Left': 'left', 'Right': 'right', 'Both': 'double'}
       )
    
    The threshold parameter determines how far the trigger needs to be pressed before a
    response is registered (e.g. the default threshold of 0.5 means a trigger needs to
    be pressed at least halfway). When the mapping allows for both triggers
    simultaneously as a response, the threshold also determines how far apart the
    triggers need to be in terms of pressure before a left or right response can be
    registered.

    Args:
        mapping (dict): A dictionary specifying the trigger responses to check for
            ('left', 'right', and/or 'both') and their corresponding response labels.
        gamepad (optional): The GameController object representing the controller to
            check for responses. If not specified, will listen for responses from all
            connected controllers.
        threshold (float, optional): The threshold specifying how far a trigger needs
            to be pressed to be considered a response (0.1 = pressed 10%, 1.0 = 
            pressed 100%). Defaults to 0.5.
        timeout (float, optional): The maximum duration (in seconds) to wait for a
            valid response. Defaults to None (no timeout).
        loop_callback (callable, optional): An optional function or method to be
            called every time the collection loop checks for new input.
    
    """
    def __init__(
        self, mapping, gamepad=None, threshold=0.5, timeout=None, loop_callback=None
    ):
        # Fallback mapping for missing controller?
        super(TriggerListener, self).__init__(timeout, loop_callback)
        self._map = {}
        self._pad = gamepad
        self._threshold = threshold # between 0 and 1
        self._lt_state = 0
        self._rt_state = 0
        self._raw_data = []
        # Parse and initialize the mapping of buttons/axes to responses
        for resp, label in mapping.items():
            resp_cleaned = resp.split(" ")[0].lower()
            if not resp_cleaned in ['left', 'right', 'both']:
                e = "'{}' is not a valid trigger response type."
                raise ValueError(e.format(resp))
            self._map[resp_cleaned] = label

    def _timestamp(self):
        # Since gamepad events have SDL timestamps, use SDL_GetTicks to mark the
        # start of the collection loop.
        return sdl2.SDL_GetTicks()

    def init(self):
        # Initializes the listener before the response collection loop
        # Flush the event queue and get the timestamp for collection start
        flush()
        self._lt_state = 0
        self._rt_state = 0
        self._raw_data = []
        self._loop_start = self._timestamp()

    def listen(self, q):
        """See :meth:`BaseResponseListener.listen`.

        """
        if self._pad:
            self._pad.update()

        # Gather trigger motion events per timestamp for the given controller
        events = []
        for e in q:
            if e.type == sdl2.SDL_CONTROLLERAXISMOTION:
                # If gamepad specified and event is from another controller, ignore it
                if self._pad and e.caxis.which != self._pad.index:
                    continue
                # Process trigger motion events
                if e.caxis.axis in TRIGGER_AXES:
                    # Update state of left/right triggers
                    if e.caxis.axis == TRIGGER_LEFT:
                        self._lt_state = e.caxis.value
                    else:
                        self._rt_state = e.caxis.value
                    # Log current state, updating last event if timestamp unchanged
                    t = e.caxis.timestamp - self._loop_start
                    event = TriggerData(t, self._lt_state, self._rt_state)
                    if len(events) and events[-1].timestamp == event.timestamp:
                        events[-1] = event
                    else:
                        events.append(event)
        
        # Log raw trigger motion and check for response criteria
        mapping = list(self._map.keys())
        single = not 'both' in mapping
        for e in events:
            self._raw_data.append(e)
            lresp = e.left >= self._threshold
            rresp = e.right >= self._threshold
            allow_resp = single or abs(e.left - e.right) >= self._threshold
            if 'both' in mapping and lresp and rresp:
                return (self._map['both'], e.timestamp)
            if 'left' in mapping and lresp and allow_resp:
                return (self._map['left'], e.timestamp)
            if 'right' in mapping and rresp and allow_resp:
                return (self._map['right'], e.timestamp)

    @property
    def raw_data(self):
        return self._raw_data
