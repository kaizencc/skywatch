// --- Configuration ---
const MAPBOX_TOKEN = window.SKYWATCH_CONFIG?.MAPBOX_TOKEN || '';
// TODO: Replace with your API Gateway URL after deploy
const API_URL = 'https://hpl9da2m4i.execute-api.us-east-1.amazonaws.com';

// Long Beach, CA (PyCon 2026 venue)
const CENTER = [-118.1514, 33.8177];

// --- Map setup ---
mapboxgl.accessToken = MAPBOX_TOKEN;

const map = new mapboxgl.Map({
  container: 'map',
  style: 'mapbox://styles/mapbox/dark-v11',
  center: CENTER,
  zoom: 9,
  pitch: 0,
});

// Track markers by ICAO24 address
const markers = {};
var spottedIcao = '';

// Community arc layer
const communityArcs = [];

map.on('load', () => {
  // Add a pulsing dot at the center (PyCon venue)
  map.addSource('venue', {
    type: 'geojson',
    data: { type: 'Point', coordinates: CENTER },
  });
  map.addLayer({
    id: 'venue-dot',
    type: 'circle',
    source: 'venue',
    paint: {
      'circle-radius': 8,
      'circle-color': '#00ff88',
      'circle-opacity': 0.6,
      'circle-stroke-width': 2,
      'circle-stroke-color': '#00ff88',
    },
  });

  // Community arcs source
  map.addSource('community-arcs', {
    type: 'geojson',
    data: { type: 'FeatureCollection', features: [] },
  });
  map.addLayer({
    id: 'community-arcs-layer',
    type: 'line',
    source: 'community-arcs',
    paint: {
      'line-color': '#00ff88',
      'line-opacity': 0.3,
      'line-width': 1,
    },
  });

  // Start polling
  updateFlights();
  setInterval(updateFlights, 5000);
  updateCommunity();
  setInterval(updateCommunity, 15000);
});

async function updateFlights() {
  try {
    const resp = await fetch(`${API_URL}/flights`);
    const data = await resp.json();
    renderFlights(data.flights || []);
  } catch (e) {
    console.error('Failed to fetch flights:', e);
  }
}

function getFlightColor(f) {
  const alt = parseFloat(f.altitude || 99999);
  const vr = parseFloat(f.vertical_rate || 0);
  if (vr < -1 && alt < 3000) return { color: '#00ccff', shadow: 'rgba(0,204,255,0.5)', label: 'arriving' };
  if (vr > 1 && alt < 5000) return { color: '#ff9900', shadow: 'rgba(255,153,0,0.5)', label: 'departing' };
  return { color: '#00ff88', shadow: 'rgba(0,255,136,0.5)', label: 'cruising' };
}

function renderFlights(flights) {
  const seen = new Set();

  for (const f of flights) {
    if (!f.longitude || !f.latitude) continue;
    const id = f.icao24;
    seen.add(id);

    const lng = parseFloat(f.longitude);
    const lat = parseFloat(f.latitude);
    const heading = parseFloat(f.heading || 0);
    const { color, shadow } = getFlightColor(f);

    const isSpotted = (id === spottedIcao);

    if (markers[id]) {
      // Update position and color
      markers[id].setLngLat([lng, lat]);
      markers[id].setRotation(heading);
      markers[id]._callsign = f.callsign;
      const el = markers[id].getElement();
      if (!el._hasClickHandler) {
        el.addEventListener('click', (e) => {
          e.stopPropagation();
          highlightFlight(id, markers[id]._callsign, lng, lat);
        });
        el._hasClickHandler = true;
      }
      if (isSpotted) {
        el.style.color = '#ff0044';
        el.style.textShadow = '0 0 16px rgba(255,0,68,0.9)';
        el.style.fontSize = '40px';
        el.style.zIndex = '10';
      } else {
        el.style.color = color;
        el.style.textShadow = `0 0 6px ${shadow}`;
        el.style.fontSize = '24px';
        el.style.zIndex = '1';
      }
    } else {
      // Create new marker
      const el = document.createElement('div');
      el.className = 'plane-marker';
      el.innerHTML = '✈';
      if (isSpotted) {
        el.style.cssText = `
          font-size: 40px;
          color: #ff0044;
          text-shadow: 0 0 16px rgba(255,0,68,0.9);
          cursor: pointer;
          z-index: 10;
        `;
      } else {
        el.style.cssText = `
          font-size: 24px;
          color: ${color};
          text-shadow: 0 0 6px ${shadow};
          cursor: pointer;
        `;
      }

      const marker = new mapboxgl.Marker({ element: el, rotation: heading })
        .setLngLat([lng, lat])
        .addTo(map);

      el.addEventListener('click', (e) => {
        e.stopPropagation();
        highlightFlight(id, f.callsign, lng, lat);
      });
      markers[id] = marker;
      markers[id]._callsign = f.callsign;
    }
  }

  // Remove stale markers
  for (const id of Object.keys(markers)) {
    if (!seen.has(id)) {
      markers[id].remove();
      delete markers[id];
    }
  }

  // Update the flight board - same data, guaranteed 1:1 match with map
  const displayed = flights
    .filter(f => f.longitude && f.latitude && f.callsign)
    .sort((a, b) => (parseFloat(b.altitude) || 0) - (parseFloat(a.altitude) || 0));
  document.getElementById('flight-count').textContent = `${displayed.length} flights overhead`;
  const list = document.getElementById('flight-list');
  list.innerHTML = displayed
    .map(f => {
      const alt = f.altitude ? `${Math.round(f.altitude)}m` : '—';
      const speed = f.velocity ? `${Math.round(f.velocity)}m/s` : '';
      const country = f.country || '';
      return `<div class="flight-row"><span class="flight-callsign">${f.callsign}</span><span class="flight-info">${country} ${speed}</span><span class="flight-alt">${alt}</span></div>`;
    })
    .join('');

  // Attach click handlers directly to each row
  list.querySelectorAll('.flight-row').forEach((row, i) => {
    row.addEventListener('click', () => {
      const f = displayed[i];
      highlightFlight(f.icao24, f.callsign, f.longitude, f.latitude);
    });
  });
}

async function updateCommunity() {
  try {
    const resp = await fetch(`${API_URL}/community`);
    const data = await resp.json();
    renderCommunityArcs(data.cities || []);
    document.getElementById('community-count').textContent =
      `${data.count || 0} PyCon attendees tracked`;
  } catch (e) {
    console.error('Failed to fetch community:', e);
  }
}

function renderCommunityArcs(cities) {
  const features = cities.map(c => {
    const dest = [parseFloat(c.longitude), parseFloat(c.latitude)];
    return {
      type: 'Feature',
      geometry: {
        type: 'LineString',
        coordinates: [CENTER, dest],
      },
      properties: { city: c.city },
    };
  });

  map.getSource('community-arcs')?.setData({
    type: 'FeatureCollection',
    features,
  });
}

let activePopup = null;

// Dismiss popup when clicking the map
map.on('click', () => {
  if (activePopup) { activePopup.remove(); activePopup = null; }
});

async function showFlightInfo(callsign, lng, lat, icao24) {
  if (!callsign) return;
  if (activePopup) activePopup.remove();

  activePopup = new mapboxgl.Popup({ offset: 20, className: 'flight-popup', closeOnClick: false })
    .setLngLat([lng, lat])
    .setHTML(`<div class="popup-loading">Loading ${callsign}...</div>`)
    .addTo(map);

  try {
    const resp = await fetch(`${API_URL}/flight/${encodeURIComponent(callsign)}`);
    const data = await resp.json();

    if (data.error && !data.operator) {
      activePopup.setHTML(`
        <div class="popup-content">
          <div class="popup-callsign">${callsign}</div>
          <div class="popup-detail">${data.error}</div>
        </div>
      `);
      generateSpotlight(callsign, icao24, data);
      return;
    }

    const origin = data.origin?.name || data.origin?.code_iata || '?';
    const dest = data.destination?.name || data.destination?.code_iata || '?';
    const route = data.route || '?';
    const operator = data.operator || '';
    const aircraft = data.aircraft_type || '';
    const status = data.status || '';

    activePopup.setHTML(`
      <div class="popup-content">
        <div class="popup-callsign">${callsign}${data.flight_number ? ` (${data.flight_number})` : ''}</div>
        ${operator ? `<div class="popup-detail">✈ ${operator}</div>` : ''}
        <div class="popup-route">${route}</div>
        ${aircraft ? `<div class="popup-detail">Aircraft: ${aircraft}</div>` : ''}
        ${status ? `<div class="popup-detail">${status}</div>` : ''}
        <a class="popup-link" href="https://flightaware.com/live/flight/${encodeURIComponent(callsign)}" target="_blank">View on FlightAware ↗</a>
      </div>
    `);

    // Generate AI spotlight for this flight
    generateSpotlight(callsign, icao24, data);
  } catch (e) {
    activePopup.setHTML(`<div class="popup-content"><div class="popup-callsign">${callsign}</div><div class="popup-detail">Lookup failed</div></div>`);
  }
}

async function generateSpotlight(callsign, icao24, flightInfo) {
  try {
    document.getElementById('spotlight-text').textContent = `Generating spotlight for ${callsign}...`;
    const resp = await fetch(`${API_URL}/spotlight`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ callsign, icao24, flight_info: flightInfo }),
    });
    const data = await resp.json();
    document.getElementById('spotlight-text').textContent = data.text || '';
    document.getElementById('spotlight').classList.add('active');
    setTimeout(() => document.getElementById('spotlight').classList.remove('active'), 2000);
  } catch (e) {
    console.error('Spotlight generation failed:', e);
  }
}

function highlightFlight(icao24, callsign, lng, lat) {
  // Set this flight as the spotted one (red highlight)
  spottedIcao = icao24;

  const marker = markers[icao24];
  if (marker) {
    const pos = marker.getLngLat();
    map.flyTo({ center: [pos.lng, pos.lat], zoom: 11, duration: 800 });
    showFlightInfo(callsign, pos.lng, pos.lat, icao24);
  } else if (lng && lat) {
    map.flyTo({ center: [parseFloat(lng), parseFloat(lat)], zoom: 11, duration: 800 });
    showFlightInfo(callsign, parseFloat(lng), parseFloat(lat), icao24);
  }
}
