import unittest
import logging
from summarizer import summarize_text, summarize_long_text, SummaryConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestSummarizer(unittest.TestCase):
    def setUp(self):
        self.sample_text = """
        OpenAI's GPT (Generative Pre-trained Transformer) models have revolutionized natural language processing. 
        These models use transformer architecture and are trained on vast amounts of text data. The training process 
        involves both supervised and unsupervised learning techniques. GPT models have demonstrated remarkable 
        capabilities in various tasks including text generation, translation, and question-answering. However, 
        they also face challenges such as potential biases in training data and the need for substantial 
        computational resources.
        """

        self.long_sample_text = """
        Artificial Intelligence (AI) has become an integral part of our daily lives. From virtual assistants like Siri and Alexa 
        to recommendation systems on streaming platforms and e-commerce websites, AI technologies are shaping how we interact with 
        digital services. Machine learning algorithms power these systems, learning from vast amounts of data to make predictions 
        and decisions.

        The impact of AI extends far beyond consumer applications. In healthcare, AI systems are assisting doctors in diagnosing 
        diseases, analyzing medical images, and predicting patient outcomes. These applications have shown promising results in 
        early disease detection and treatment planning. The healthcare industry is particularly excited about AI's potential to 
        process and analyze large volumes of medical data more quickly and accurately than human practitioners.

        In the business world, AI is transforming operations across industries. Companies are using AI for everything from 
        automating routine tasks to making complex business decisions. Predictive analytics powered by AI helps businesses 
        forecast market trends, optimize supply chains, and personalize customer experiences. The financial sector has embraced 
        AI for fraud detection, risk assessment, and algorithmic trading.

        However, the widespread adoption of AI also raises important ethical considerations. Questions about privacy, bias in AI 
        systems, and the impact of automation on employment are at the forefront of public discourse. As AI systems become more 
        sophisticated, ensuring their decisions are transparent, fair, and accountable becomes increasingly important. The challenge 
        lies in balancing technological advancement with ethical considerations and human values.

        Educational institutions and workplaces are adapting to prepare people for an AI-driven future. New curricula are being 
        developed to teach AI literacy, and professionals across fields are upskilling to work alongside AI systems. The future 
        workforce will need to combine human creativity and critical thinking with AI literacy and technical skills.
        """

    def test_short_text_summarization(self):
        """Test summarization of short text"""
        config = SummaryConfig(
            model="gpt-oss:20b",
            temperature=0.7,
            max_tokens=200,
            length="short"
        )

        summary = summarize_text(self.sample_text, config)
        self.assertIsNotNone(summary)
        self.assertTrue(len(summary) > 0)

    def test_long_text_summarization(self):
        """Test summarization of long text with different configurations"""
        configs = {
            "short": SummaryConfig(
                model="gpt-oss:20b",
                temperature=0.7,
                max_tokens=200,
                length="short"
            ),
            "medium": SummaryConfig(
                model="gpt-oss:20b",
                temperature=0.7,
                max_tokens=400,
                length="medium"
            ),
            "long": SummaryConfig(
                model="gpt-oss:20b",
                temperature=0.7,
                max_tokens=800,
                length="long"
            )
        }

        for length, config in configs.items():
            with self.subTest(length=length):
                summary = summarize_long_text(self.long_sample_text, config)
                self.assertIsNotNone(summary)
                self.assertTrue(len(summary) > 0)

    def test_automatic_method_selection(self):
        """Test automatic selection between regular and long text summarization"""
        config = SummaryConfig(
            model="gpt-oss:20b",
            temperature=0.7,
            max_tokens=400,
            length="medium"
        )

        # Test with short text
        summary_short = summarize_text(self.sample_text, config)
        self.assertIsNotNone(summary_short)

        # Test with long text
        summary_long = summarize_long_text(self.long_sample_text, config)
        self.assertIsNotNone(summary_long)

if __name__ == '__main__':
    unittest.main()
