
import sys
import subprocess
import os.path
import json
import re

directory = '/home/public'

class Streamer:
	def __init__(self, filename):
		self.filename = filename
		if not os.path.isfile(filename):
			raise Exception('File does not exist: ' + filename)

	def getDescription(self):
		args = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', self.filename]
		out = subprocess.check_output(args, shell=False);
		duration = float(out);
		return {'duration': duration}

	def getWebmStream(self, hd=False, start='', stop=''):
		filters = []
		if hd:
			filters+= ['scale=-1:min(ih*1920/iw\,1080)']
			filters+= ['pad=1920:1080:(1920-iw)/2:(1080-ih)/2:black']

		if re.match('^[^\"\'\\[\\]]+$', self.filename):
			srt = os.path.splitext(self.filename)[0]+'.srt'
			if os.path.isfile(srt):
				filters+= ['subtitles='+srt+':charenc=CP1252']
			elif 'codec_type=subtitle' in subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', self.filename]).decode():
				filters+= ['subtitles='+self.filename]

		args = ['ffmpeg']
		if start:
			args+= ['-ss', start]
		args+= ['-i', self.filename]
		if stop:
			args+= ['-to', stop]
		if len(filters):
			args+= ['-vf', ','.join(filters)]
		args+= ['-v', 'error', '-copyts', '-c:v', 'libvpx', '-b:v', '4M', '-crf', '16', '-quality', 'realtime', '-cpu-used', '8', '-c:a', 'libvorbis', '-f', 'webm', '-']

		proc = subprocess.Popen(args, stdin=None, stdout=subprocess.PIPE, shell=False)
		return proc.stdout
