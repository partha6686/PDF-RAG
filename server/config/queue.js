const { Queue, Worker } = require('bullmq');
const { redisConfig } = require('./redis');

// Queue configuration
const queueOptions = {
  connection: redisConfig,
  defaultJobOptions: {
    removeOnComplete: 10, // Keep last 10 completed jobs
    removeOnFail: 50,     // Keep last 50 failed jobs
    attempts: 3,          // Retry failed jobs 3 times
    backoff: {
      type: 'exponential',
      delay: 2000,
    },
  },
};

// Create PDF processing queue
const pdfProcessingQueue = new Queue('pdf-processing', queueOptions);

// Queue event handlers
pdfProcessingQueue.on('error', (error) => {
  console.error('Queue error:', error);
});

pdfProcessingQueue.on('waiting', (job) => {
  console.log(`Job ${job.id} is waiting`);
});

pdfProcessingQueue.on('active', (job) => {
  console.log(`Job ${job.id} is now active`);
});

pdfProcessingQueue.on('completed', (job, result) => {
  console.log(`Job ${job.id} completed with result:`, result);
});

pdfProcessingQueue.on('failed', (job, error) => {
  console.error(`Job ${job.id} failed:`, error);
});

module.exports = {
  pdfProcessingQueue,
  queueOptions
};