const Redis = require('redis');

// Redis client configuration
const redisConfig = {
  host: process.env.REDIS_HOST || 'localhost',
  port: process.env.REDIS_PORT || 6379,
  retryDelayOnFailover: 100,
  enableReadyCheck: false,
  maxRetriesPerRequest: null,
};

// Create Redis connection
const createRedisConnection = () => {
  const client = Redis.createClient(redisConfig);
  
  client.on('error', (err) => {
    console.error('Redis connection error:', err);
  });
  
  client.on('connect', () => {
    console.log('Connected to Redis');
  });
  
  return client;
};

module.exports = {
  redisConfig,
  createRedisConnection
};