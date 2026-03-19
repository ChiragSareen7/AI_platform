const express = require('express');
const dashboardController = require('../controllers/dashboard.controller');

const router = express.Router();

router.get('/logs/summary', dashboardController.getLogsSummary);
router.get('/prompts/performance', dashboardController.getPromptPerformance);
router.get('/recommendations', dashboardController.getRecommendations);

module.exports = router;
