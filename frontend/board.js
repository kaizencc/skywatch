// --- Flight board and spotlight logic ---

let lastSpotlightText = '';

// --- Community city form ---
function toggleCityForm() {
  document.getElementById('city-form').classList.toggle('hidden');
  document.getElementById('city-input').focus();
}

async function submitCity() {
  const input = document.getElementById('city-input');
  const city = input.value.trim();
  if (!city) return;

  try {
    const geoResp = await fetch(
      `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(city)}.json?access_token=${MAPBOX_TOKEN}&limit=1`
    );
    const geoData = await geoResp.json();
    const feature = geoData.features?.[0];

    if (!feature) {
      alert('City not found. Try again.');
      return;
    }

    const [lon, lat] = feature.center;
    const placeName = feature.place_name || city;

    await fetch(`${API_URL}/community`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ city: placeName, lat, lon }),
    });

    input.value = '';
    document.getElementById('city-form').classList.add('hidden');
    updateCommunity();
  } catch (e) {
    console.error('Failed to add city:', e);
    alert('Something went wrong. Try again.');
  }
}
