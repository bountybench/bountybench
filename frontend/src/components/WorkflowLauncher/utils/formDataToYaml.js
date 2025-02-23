import yaml from 'js-yaml';

export const formDataToYaml = (formData, useMockModel) => {
  const config = {
    workflow_type: formData.workflow_name.toLowerCase().replace(/ /g, '_'),
    tasks: formData.tasks.map(task => ({
      task_dir: `bountybench/${task.task_dir.replace(/^bountybench\//, '')}`,
      bounty_number: task.bounty_number
    })),
    phase_iterations: parseInt(formData.iterations),
    trials_per_config: 1, // Default to 1
    models: [
      {
        name: formData.model,
        helm: formData.use_helm
      }
    ],
    use_mock_model: useMockModel,
  };

  if (formData.vulnerability_type) {
    config.vulnerability_type = [formData.vulnerability_type];
  }

  return yaml.dump(config);
};