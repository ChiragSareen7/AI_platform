const express = require('express');
const preferencesController = require('../controllers/preferences.controller');

const router = express.Router();

router.get('/preferences', preferencesController.getPreferences);
router.post('/preferences', preferencesController.updatePreferences);

module.exports = router;
