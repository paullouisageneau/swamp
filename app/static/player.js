// Copyright (C) 2017 by Paul-Louis Ageneau
// paul-louis (at) ageneau (dot) org
//
// This file is part of Swamp.
//
// Swamp is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as
// published by the Free Software Foundation, either version 3 of
// the License, or (at your option) any later version.
//
// Swamp is distributed in the hope that it will be useful, but
// WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public
// License along with Swamp.
// If not, see <http://www.gnu.org/licenses/>

var video = document.getElementById('video');
var videoSource = document.createElement('source');
var player = document.getElementById('player');
var castlinks = document.getElementById('castlinks');
var progress = document.getElementById('progress');
var progressbar = document.getElementById('progressbar');
var playbutton = document.getElementById('playbutton');
var videoUrl = "";
var videoTime = 0;
var videoHeight = -1;
var videoBaseTime = 0;
var videoDuration = -1;
var audioStream = 0;

video.appendChild(videoSource);

video.ontimeupdate = function() {
	// We need to handle relative and absolute timestamps due to buggy browser implementations
	if(this.currentTime < videoBaseTime/2) videoTime = videoBaseTime + this.currentTime;
	else videoTime = this.currentTime;
	if(videoDuration > 0)
		updateTimer();
}

video.onplay = function() {
	scalePlayer();
	playbutton.src = playbutton.src.substr(0, playbutton.src.lastIndexOf('/') + 1) + 'pause.png';
}

video.onpause = function() {
	playbutton.src = playbutton.src.substr(0, playbutton.src.lastIndexOf('/') + 1) + 'play.png';
}

video.onclick = function() {
	toggleFullscreen();
}

playbutton.onclick = function() {
	if(video.paused) video.play();
	else video.pause();
}

progress.onmousedown = function(evt) {
	evt.preventDefault();
	loadVideo(videoUrl, videoDuration*(evt.clientX-this.offsetParent.offsetLeft)/progress.clientWidth);
};

document.onkeydown = function(evt) {
	evt = evt || window.event;
	switch(evt.which || evt.keyCode) {
	case 32: // space
		if(video.paused) video.play();
		else video.pause();
		break;
	case 37: // left
		loadVideo(videoUrl, videoTime-30);
		break;
	case 39: // right
		loadVideo(videoUrl, videoTime+30);
		break;
	default:
		return;
	}
	evt.preventDefault();
}

window.onresize = function() {
	scalePlayer();
}

function formatTime(time) {
	var seconds = Math.floor(time%60);
	var minutes = Math.floor(time/60)%60;
	var hours = Math.floor(time/3600);
	return ("0"+hours).slice(-2)+":"+("0"+minutes).slice(-2)+":"+("0"+seconds).slice(-2);
}

function loadVideo(url, time) {
	if(time < 0)
		time = 0;
	if(videoDuration >= 0 && time > videoDuration)
		time = videoDuration;

	videoUrl = url;
	videoBaseTime = videoTime = time;
	updateTimer();

	videoSource.setAttribute('src', videoUrl+"?play&audio="+audioStream+"&start="+formatTime(videoTime));
	video.load();
	video.play();

	if(videoDuration < 0) {
		var request = new XMLHttpRequest();
		request.open('GET', videoUrl+"?playinfo", true);
		request.onload = function() {
			if (this.status >= 200 && this.status < 400) {
			var data = JSON.parse(this.response);
				videoDuration = data.duration;
			}
		};
		request.send();
	}
}

function updateTimer() {
	percent = (videoDuration >= 0 ? 100*videoTime/videoDuration : 0);
	progressbar.style.width = percent + "%";
	document.getElementById("timer").innerHTML = formatTime(videoTime);
}

function scalePlayer() {
	if(videoHeight < 0) videoHeight = video.clientHeight;
	var h = window.innerHeight-64;
	if(videoHeight > h) video.style.height = h+'px';
	else if(videoHeight > 0) video.style.height = videoHeight+'px';
}

function toggleFullscreen() {
	var element = video;
	if (!document.fullscreenElement &&
      !document.mozFullScreenElement && !document.webkitFullscreenElement && !document.msFullscreenElement ) {  
		if (element.requestFullscreen) {
			element.requestFullscreen();
		} else if (element.msRequestFullscreen) {
			element.msRequestFullscreen();
		} else if (element.mozRequestFullScreen) {
			element.mozRequestFullScreen();
		} else if (element.webkitRequestFullscreen) {
			element.webkitRequestFullscreen(Element.ALLOW_KEYBOARD_INPUT);
		}
	} else {
		if (document.exitFullscreen) {
			document.exitFullscreen();
		} else if (document.msExitFullscreen) {
			document.msExitFullscreen();
		} else if (document.mozCancelFullScreen) {
			document.mozCancelFullScreen();
		} else if (document.webkitExitFullscreen) {
			document.webkitExitFullscreen();
		}
	}
}

function requestCastLinks() {
	var request = new XMLHttpRequest();
	request.open('GET', videoUrl+"?castinfo", true);
	request.onload = function() {
		if (this.status >= 200 && this.status < 400) {
			var data = JSON.parse(this.response);
			castlinks.innerHTML = "";
			if(data.devices.length > 0) {
				castlinks.innerHTML+= " - Cast:&nbsp;";
				for (var i = 0; i < data.devices.length; i++) {
					castlinks.innerHTML+= "<a href=\"#\" onclick=\"requestCast('"+data.devices[i]+"');return false;\">"+data.devices[i]+"</a>&nbsp;";
				}
			}
		};
	}
	request.send();
}

function requestCast(device) {
	video.pause();
	var request = new XMLHttpRequest();
	request.open('GET', videoUrl+"?cast"+(device ? "="+device : "")+"&hd&start="+formatTime(videoTime), true);
	request.onload = function() {
		// TODO
	};
	request.send();
}
