---
layout: post
title: "Grok Latest APIs and LLMs Pricing October 2025"
author: professor-xai
categories: [grok,grok-api,llm, api, ai-agents, cost,pricing]
image: assets/images/grok-api-pricing-october-2025.jpg
---

# Grok API Pricing October 2025: Complete Guide to Models, Features, and Costs

*October 2025*

xAI's Grok API continues to evolve with new models and pricing structures designed to meet diverse developer needs. This comprehensive guide covers everything you need to know about Grok API pricing as of October 2025.

## 🚀 New Model Releases

### Grok 4 Fast Series
xAI has introduced two new cost-efficient reasoning models:

**grok-4-fast-reasoning**  
- **Capabilities**: Advanced reasoning with lightning-fast performance  
- **Context Window**: 2,000,000 tokens  
- **Pricing**: $0.20 per million input tokens · $0.50 per million output tokens  
- **Rate Limits**: 4M tokens per minute · 480 requests per minute  

**grok-4-fast-non-reasoning**  
- **Capabilities**: Cost-optimized non-reasoning variant  
- **Context Window**: 2,000,000 tokens  
- **Pricing**: $0.20 per million input tokens · $0.50 per million output tokens  
- **Rate Limits**: 4M tokens per minute · 480 requests per minute  

### Specialized Coding Model
**grok-code-fast-1**  
- **Description**: Lightning-fast reasoning model built for agentic coding  
- **Context Window**: 256,000 tokens  
- **Pricing**: $0.20 per million input tokens · $1.50 per million output tokens  
- **Rate Limits**: 2M tokens per minute · 480 requests per minute  

## 📊 Complete Model Pricing Table

### Language Models

| Model | Context Window | Rate Limits | Input Pricing | Output Pricing |
|-------|----------------|-------------|---------------|----------------|
| grok-code-fast-1 | 256,000 tokens | 2M ipm · 480 rpm | $0.20 / 1M tokens | $1.50 / 1M tokens |
| grok-4-fast-reasoning | 2,000,000 tokens | 4M ipm · 480 rpm | $0.20 / 1M tokens | $0.50 / 1M tokens |
| grok-4-fast-non-reasoning | 2,000,000 tokens | 4M ipm · 480 rpm | $0.20 / 1M tokens | $0.50 / 1M tokens |
| grok-4-0709 | 256,000 tokens | 2M ipm · 480 rpm | $3.00 / 1M tokens | $15.00 / 1M tokens |
| grok-3-mini | 131,072 tokens | 480 ipm | $0.30 / 1M tokens | $0.50 / 1M tokens |
| grok-3 | 131,072 tokens | 600 ipm | $3.00 / 1M tokens | $15.00 / 1M tokens |
| grok-2-vision-1212 (us-east-1) | 32,768 tokens | 600 ipm | $2.00 / 1M tokens | $10.00 / 1M tokens |
| grok-2-vision-1212 (eu-west-1) | 32,768 tokens | 50 ips | $2.00 / 1M tokens | $10.00 / 1M tokens |

### Image Generation Models

**grok-2-image-1212**  
- **Pricing**: $0.07 per image  
- **Rate Limit**: 300 images per minute  

## 🔍 Search Features Pricing

### Live Search
- **Cost**: $25 per 1,000 sources requested
- **Billing**: Each source used (Web, X, News, RSS) counts as one request
- **Examples**:
  - 1 source: $0.025
  - 4 sources: $0.10
- **Tracking**: Check `response.usage.num_sources_used` in API response

### Documents Search
- **Documents Search**: $2.50 per 1,000 requests
- **File Storage**: Free
- **Collections Storage**: Free

## ⚡ Grok 4 Important Updates

### Key Differences from Grok 3
- **Reasoning Model Only**: Grok 4 operates exclusively as a reasoning model with no non-reasoning mode
- **Unsupported Parameters**: `presencePenalty`, `frequencyPenalty`, and `stop` parameters are not supported
- **No Reasoning Effort**: The `reasoning_effort` parameter is not available in Grok 4

### Knowledge Cut-off
- **Grok 3 & Grok 4**: Both models have knowledge up to November 2024
- **Realtime Information**: Requires Live Search integration for current events

## 💡 Model Capabilities & Features

### Input/Output Modalities
- **Text-to-Text (T→T)**: All current models support text input and output
- **Image Input**: Supported by vision models with specific limitations
- **Mixed Input**: Text and image inputs can be combined in any order

### Image Input Specifications
- **Maximum Image Size**: 20MiB
- **Maximum Number of Images**: No limit
- **Supported Formats**: JPG/JPEG or PNG
- **Flexible Input Order**: Text prompts can precede or follow image inputs

### Context Window Management
- **Variable Sizes**: Ranging from 32,768 to 2,000,000 tokens depending on model
- **Cached Prompt Tokens**: Automatic caching reduces costs for repeated prompts
- **Usage Tracking**: Monitor cached token consumption in the "usage" object

## 🎯 Best Practices for Cost Optimization

1. **Use Cached Prompts**: Enable automatic caching for repeated requests
2. **Choose Appropriate Model**: Select based on task complexity and budget
3. **Monitor Source Usage**: Track Live Search sources to control costs
4. **Leverage Context Windows**: Use larger context models for complex conversations
5. **Consider Grok 4 Fast**: New models offer significant cost savings for reasoning tasks

## 📈 Pricing Summary

The October 2025 pricing introduces significant improvements in cost-efficiency, particularly with the new Grok 4 Fast series offering reasoning capabilities at substantially lower prices compared to previous generations.

For the most up-to-date pricing and detailed specifications, always check the official xAI Console and API documentation.

---

*Note: All prices are subject to change. Please refer to official xAI documentation for the most current pricing information.*
