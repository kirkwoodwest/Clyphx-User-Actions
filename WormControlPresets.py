"""
WORM CONTROL: Presets

This preset restore system is intented to use for utilizing the loaduser functionality
of clyphx for many tracks and restore its properties. For example you can save the first device of any number of tracks...

These user actions are compatible with Clyphx Pro 1.6

How To Use:

-- Saving A Preset
---------------------------------
WCP_SAVE
[Preset ID] 1-5/WCP_SAVE  
Saves the preset into song memory tracks 1-5. This works like any other track action.

WCP_SAVE_COPY
[] 1-5/WCP_SAVE_COPY
Saves the preset into the clip itself using a python serialization library. When executed it will turn the action into WCP_LOAD_COPY ||(

WCP_LOAD
[PRESET ID] WCP_LOAD
Loads all the ADG files into memory 1 by one. e.g. TRACK_ID/DEV(1) SEL; WAIT 1; LOADUSER "PRESET_NAME.adg"; WAIT 4;

WCP_LOAD_COPY
[] WCP_LOAD_COPY ||(....
Desealizes the date in the xtrigger name and starts loading the presets  ADG files into memory 1 by one. e.g. TRACK_ID/DEV(1) SEL; WAIT 1; LOADUSER "PRESET_NAME.adg"; WAIT 4;

WCP_CLEAR
[] WCP_CLEAR
Clears out any memory in song() data and python memory of any presets.

WCP_BACKUP
[] WCP_BACKUP
Stores a backup of the presets that are in memory to disk. Currently writes it to the NativeKontrol/Clyphx Folder. WCP_Backup

WCP_RESTORE
[] WCP_RESTORE
Restores a backup of the track. Loads same file that is saved from backup. This is useful if you would like 
to manually edit a preset definition for a song.

WCP_PRESET_SWAP_TIME
[ ] WCP_PRESET_SWAP_TIME 4
Sets the swap time to for between presets. If somehow you need a longer delay.

Code: This probably uses lots of code from a lot of places. Particularly Clyphx Pro and the user actions. Feel free to use it.
and I'm releasing myself responsible for any data corruption or glitches as a result of using this software. Swapping presets
while generating realtime audio is incredibly cpu disruptive. USE AT YOUR OWN RISK.
"""

# Import UserActionsBase to extend it.
import pickle

from ClyphX_Pro.clyphx_pro.UserActionsBase import UserActionsBase
import json
import os
import re

WCP_PRESET_HEADER = "Worm Control Presets"
WCP_BACKUP_FILE_NAME = "WCP_Backup.json"
DEBUG = False
# Use Log.

# Your class must extend UserActionsBase.
class WormControlPresets(UserActionsBase):
    """ ExampleActions provides some example actions for demonstration purposes. """

    # Your class must implement this method.
    def create_actions(self):
        self.data = {}
        self.preset_temp_data = []
        self.preset_swap_time = 3

        #Worm Control Presets 
        self.add_track_action('wcp_save', self.preset_save)
        self.add_track_action('wcp_save_copy', self.preset_save_copy)
        self.add_global_action('wcp_load', self.preset_load)
        self.add_global_action('wcp_load_copy', self.preset_load_copy)
        self.add_global_action('wcp_clear', self.preset_clear)
        self.add_global_action('wcp_backup', self.preset_backup)
        self.add_global_action('wcp_restore', self.preset_restore)
        self.add_global_action('wcp_preset_swap_time', self.set_swap_time)

    def set_swap_time(self, action_def, args):
        #Sets the swap time for preset recall... This is the waits between loading the preset and selecting the next one.
        self.preset_swap_time = int(args)

    def preset_save(self,action_def, args):
        self.preset_save_base(action_def, args, False)

    def preset_save_copy(self,action_def, args):
        self.preset_save_base(action_def, args, True)
        
    def preset_save_base(self, action_def, args, do_copy):
      
        last_track = self.is_last_track(action_def)

        #Check to see if track is in data.
        track_in_data = False
        for track_item in self.preset_temp_data:
            if track_item == action_def['track']:
                track_in_data = True

        #If we don't have the track then add the track...
        if track_in_data == False:     
            self.preset_temp_data.append(action_def['track'])

        if last_track:
           
            preset_name = action_def['ident']
            preset_name = preset_name.lower()

            preset_data = []
                   
            if preset_name == None:
                self.canonical_parent.show_message('WCP_SAVE: Clyphx identifier is missing.') 
                return
                
            for track in self.preset_temp_data:
                track_name = track.name
 
                if DEBUG:
                    self.canonical_parent.log_message('device lookup %s ' % track_name)

                #Only saving the first device name in the preset
                devices = track.devices
                if devices[0]:
                    device_preset_name = devices[0].name
                else:
                    continue

                device_preset_data = {'track_name':track_name, 'preset':device_preset_name}
                preset_data.append(device_preset_data)
                
            #loop thru data
            data = self.get_data()
            data[preset_name] = preset_data

            #Save Data
            self.set_data(data)

            data_pickled = pickle.dumps(preset_data)
            self.log_var('data_pickled', data_pickled)

            if do_copy:
                self._update_xtrigger_name(action_def, preset_data)
            else:
                self._update_xtrigger_name(action_def, None)

    def preset_load(self, action_def, args):
        self.preset_load_base(action_def, args, False)

    def preset_load_copy(self, action_def, args):
        self.preset_load_base(action_def, args, True)
        
    def preset_load_base(self, action_def, args, do_copy):

        preset_name = action_def['ident']

        data = self.get_data()

        preset_data = None

        if do_copy:
            #read data from args.. strip out first || and
            raw_pickle_data = action_def['xtrigger'].name.split("||")[1]
            self.canonical_parent.log_message('preset_data = pickle.loads(data): %s' % data)
            preset_data = pickle.loads(raw_pickle_data)
            data[preset_name] = preset_data

            #Save Data into memory because thats what we do...
            self.set_data(data)            
        else:
            preset_data = data[preset_name]
           
        action_list = ''
        if preset_data:
            for preset in preset_data:
                track_name = preset['track_name']
                action_list = action_list + ('"%s"/DEV(1) OFF; ' % track_name)
        
        if preset_data:
            for preset in preset_data:
                track_name = preset['track_name']
                device_preset_name = preset['preset']
                swap_time = self.preset_swap_time 
                action_list = action_list + ('WAIT %s; "%s"/DEV(1) SEL; WAIT 1; LOADUSER "%s.adg"; ' % (swap_time, track_name, device_preset_name))
                #action_list = action_list + ('WAIT %s; "%s"/DEV(1) SEL; WAIT 1; SWAP "%s.adg"; ' % (swap_time, track_name, device_preset_name))
        
        action_list = action_list + ('WAIT %s; SCENE SEL "%s"' % (swap_time, preset_name))
        
        self.canonical_parent.show_message('WCP RECALL: %s' % preset_name)
        self.log('Action List: %s' % action_list)
    
        self.canonical_parent.clyphx_pro_component.trigger_action_list(action_list)

    def preset_clear(self, action_def, args):        
        self.data = {} 
        self.song().set_data(WCP_PRESET_HEADER, None)
        self.canonical_parent.show_message('WCP: ALL PRESETS CLEARED!')

    def preset_backup(self, action_def, args):        

        try:
            self.canonical_parent.log_message('Backing up 0! %s' % self.data) 
        except:
            self.canonical_parent.log_message('preset backup failed no data...')

        data = self.get_data()
        self.canonical_parent.log_message('Backing up 1! %s' % data) 

        s_path = os.path.join(os.path.expanduser('~'), 'nativeKONTROL', 'ClyphX_Pro')
        filename = os.path.join(s_path, WCP_BACKUP_FILE_NAME)
        
        f = open(filename,"w+")
        json.dump(data, f, indent=4)
        f.close()
    
    def preset_restore(self, action_def, args):
 
        filename = os.path.join(os.path.expanduser('~'), WCP_BACKUP_FILE_NAME)       
        self.canonical_parent.log_message('filename: %s' % filename) 
        f = open(filename,"r")
        
        self.canonical_parent.log_message('f: %s' % f) 
        data = json.load(f)
        self.set_data(data)

        f.close()
        self.canonical_parent.show_message('Restored data! %s' % self.data) 
           
    def get_data(self):
        '''
        self.data = {  
            "Joker": [
                {"track_name": "mono1",
                "preset": "Fresh Drum"
                },
                {"track_name": "mono2",
                "preset": "Fresh Drum 3"
                }
            ],
            "Fresh Track": [
                {"track_name": "mono1",
                "preset": "Fresh Drum"
                },
                {"track_name": "mono2",
                "preset": "Fresh Drum 3"
                }
            ],
        }
        '''

        #Get data from File in memory
        stored_data = self.song().get_data(WCP_PRESET_HEADER, None)
        if stored_data == None and len(self.data) == 0:
            data = {}
        else:  
            data = stored_data

        self.data = data
        return self.data

    def set_data(self, data):
        self.data = data
        self.song().set_data(WCP_PRESET_HEADER, data)

    def is_last_track(self, action_def):
        '''Returns bool True if its the last track in the xtrigger track list.'''
        
        last_track = False
        track = action_def['track']
        track_name = track.name
        #Get index of track (clyphx indexes at 1)
        track_index = 1 
        for track_item in self.song().tracks:
            if track_item == track:
                break
            track_index = track_index + 1 

        xtrigger_name = action_def['xtrigger'].name
        x = re.search(r"([\"\w\d]+)(?:\/)",xtrigger_name)

        last_track_id = None

        if x.group(1): 
            last_track_id = x.group(1)

        #Determine if # or string. 
        track_id_is_number = True
        if str(last_track_id)[0] == "\"":
            track_id_is_number = False

        if track_id_is_number:
            if int(last_track_id) == int(track_index):
                last_track = True
                self.log('---5.5a---- last_track: %s' % str(last_track))
        else:
            stripped_string = str(last_track_id).replace('"','')
            if stripped_string == track_name:
                last_track = True

        return last_track


    @staticmethod
    def _update_xtrigger_name(action_def, data):
        """ Updates the xclip/xscene's name to remove the snap action specification so
        that it can recall snaps. This assumes that the snap action is the first action
        in an action list. """
        if not action_def['xtrigger_is_nameable']:
            return
        xtrig = action_def['xtrigger']
        action_spec = xtrig.name.split(';')[0]

        if data:
            data_pickled = pickle.dumps(data)
            action = 'WCP_LOAD_COPY ||%s' % (data_pickled)
            xtrig.name = '[%s] %s' % (action_def['ident'], xtrig.name.replace(action_spec, action))
        else:
            xtrig.name = '[%s] %s' % (action_def['ident'], xtrig.name.replace(action_spec, 'WCP_LOAD'))

    def log(self, message):
        if DEBUG == True:
           self.canonical_parent.log_message(message)

    def log_var(self, name, value):
        self.log('%s: %s' % (name,value))