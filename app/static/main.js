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

window.onload = function() {
	var list = document.getElementById('list');
	if(list) {
		var elements = list.getElementsByTagName('td');
		for(i in elements) {
			var a = elements[i].getElementsByTagName('a');
			if(a.length) {
				(function(href) {
					elements[i].onclick = function() {
						document.location.href = href;
					}
				})(a[0].href);
				elements[i].style.cursor = 'pointer';
			}
		}
	}
};
