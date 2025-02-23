import yaml from 'js-yaml';

export const formDataToYaml = (formData) => {
  const config = {
    workflow_type: formData.workflow_name.toLowerCase().replace(/ /g, '_'),
    tasks: [
      {
        task_dir: `bountybench/${formData.task_dir.replace(/^bountybench\//, '')}`,
        bounty_number: formData.bounty_number
      }
    ],
    phase_iterations: parseInt(formData.iterations),
    trials_per_config: 1, // Default to 1
    models: [
      {
        name: formData.model,
        helm: formData.use_helm
      }
    ]
  };

  if (formData.vulnerability_type) {
    config.vulnerability_type = [formData.vulnerability_type];
  }

  // If there are multiple tasks, add them to the tasks array
  if (formData.additional_tasks) {
    formData.additional_tasks.forEach(task => {
      config.tasks.push({
        task_dir: `bountybench/${task.task_dir.replace(/^bountybench\//, '')}`,
        bounty_number: task.bounty_number
      });
    });
  }

  return yaml.dump(config);
};