const express = require('express');
const queryController = require('../controllers/query.controller');

const router = express.Router();

router.post('/query', queryController.runQuery);

module.exports = router;
