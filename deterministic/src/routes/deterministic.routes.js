const express = require('express');
const deterministicController = require('../controllers/deterministic.controller');

const router = express.Router();

router.post('/deterministic-query', deterministicController.deterministicQuery);

module.exports = router;
