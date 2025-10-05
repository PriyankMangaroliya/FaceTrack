// "use strict";

// // initialize map
// var map = new GMaps({
//   div: '#map',
//   lat: 23.078960,
//   lng: 72.623013,
//   zoom: 8
// });
// // Added markers to the map
// map.addMarker({
//   lat: 23.078960,
//   lng: 72.623013,
//   title: 'Airport',
//   infoWindow: {
//     content: '<h6>Airport</h6><p>Sardar Vallabhbhai Patel International Airport, <br>Ahmedabad</p><p><a target="_blank" href="http://example.com">Website</a></p>'
//   }
// });
// map.addMarker({
//   lat: 22.291343,
//   lng: 70.801418,
//   title: 'Bus Stop',
//   infoWindow: {
//     content: '<h6>Bus Stop</h6><p>Rajkot GSRTC Bus Stop</p><p><a target="_blank" href="https://example.com/">Website</a></p>'
//   }
// });

// map.addMarker({
//   lat: 22.322411,
//   lng: 73.180935,
//   title: 'University',
//   infoWindow: {
//     content: '<h6>University</h6><p>M S Uni Head Office, Officers Railway Colony, Pratapgunj, Vadodara, Gujarat 390002, India</p><p><a target="_blank" href="http://example.com/">Website</a></p>'
//   }
// });

// map.addMarker({
//   lat: 21.219507501716457,
//   lng: 72.89320663378099,
//   title: 'Surat',
//   infoWindow: {
//     content: '<h6>University</h6><p>M S Uni Head Office, Officers Railway Colony, Pratapgunj, Vadodara, Gujarat 390002, India</p><p><a target="_blank" href="http://example.com/">Website</a></p>'
//   }
// });
"use strict";

// Initialize map
var map = new GMaps({
  div: '#map',
  lat: 22.2587,
  lng: 71.1924,
  zoom: 8
});

// Define addresses
var addresses = [
  'Surat, Gujarat',
  'Mumbai, Maharashtra',
  'Ahmedabad, Gujarat'
];

// Geocode addresses and add markers to the map
addresses.forEach(function(address) {
  GMaps.geocode({
    address: address,
    callback: function(results, status) {
      if (status == 'OK') {
        var latlng = results[0].geometry.location;
        map.addMarker({
          lat: latlng.lat(),
          lng: latlng.lng(),
          title: address,
          infoWindow: {
            content: '<h6>' + address + '</h6><p>Latitude: ' + latlng.lat() + '<br>Longitude: ' + latlng.lng() + '</p>'
          }
        });
      } else {
        console.error('Geocode was not successful for the following reason: ' + status);
      }
    }
  });
});
