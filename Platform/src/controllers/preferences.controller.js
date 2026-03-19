const preferencesService = require('../services/preferences.service');

async function getPreferences(req, res) {
  try {
    const preferences = await preferencesService.readPreferences();
    return res.json(preferences);
  } catch (err) {
    console.error('[Preferences] get error:', err);
    return res.status(500).json({ error: 'Failed to load preferences' });
  }
}

async function updatePreferences(req, res) {
  try {
    const body = req.body || {};
    const preferences = await preferencesService.writePreferences(body);
    return res.json(preferences);
  } catch (err) {
    console.error('[Preferences] update error:', err);
    return res.status(500).json({ error: 'Failed to save preferences' });
  }
}

module.exports = {
  getPreferences,
  updatePreferences,
};
