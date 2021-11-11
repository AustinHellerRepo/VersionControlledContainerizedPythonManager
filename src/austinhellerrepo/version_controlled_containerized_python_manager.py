from austin_heller_repo.docker_manager import DockerManager
from austin_heller_repo.git_manager import GitManager, GitLocalRepositoryInstance
from austin_heller_repo.threading import TimeoutThread
from typing import List, Tuple, Dict


class DockerContainerInstanceTimeoutException(Exception):

	def __init__(self, *args: object):
		super().__init__(*args)


class VersionControlledContainerizedPythonInstance():

	def __init__(self):
		raise NotImplementedError()

	def get_output(self) -> str:
		raise NotImplementedError()

	def wait(self):
		raise NotImplementedError()


class VersionControlledContainerizedPythonManager():

	def __init__(self, *, git_manager: GitManager):

		self.__git_manager = git_manager

	def run_python_script(self, *, git_repo_clone_url: str, script_file_path: str, script_arguments: List[str], timeout_seconds: float) -> str:

		if not self.__git_manager.is_repository_cloned_locally(
			git_url=git_repo_clone_url
		):
			git_local_repository_instance = self.__git_manager.clone(
				git_url=git_repo_clone_url
			)
		else:
			git_local_repository_instance = self.__git_manager.get_existing_local_repository_instance_from_url(
				git_url=git_repo_clone_url
			)
			if git_local_repository_instance.is_remote_commit_different(
				git_url=git_repo_clone_url
			):
				# TODO perform lock on git repo directory
				git_local_repository_instance = self.__git_manager.clone(
					git_url=git_repo_clone_url
				)

		docker_manager = DockerManager(
			dockerfile_directory_path=git_local_repository_instance.get_directory_path()
		)

		git_project_name = GitManager.get_project_name_from_git_url(
			git_url=git_repo_clone_url
		)

		docker_container_instance = docker_manager.start(
			name=f"vccpm_{git_project_name.lower()}"
		)

		concat_script_arguments = ""
		for script_argument_index, script_argument in enumerate(script_arguments):
			if script_argument_index != 0:
				concat_script_arguments += " "
			concat_script_arguments += f"{script_argument}"

		output = None  # type: bytes

		def timeout_thread_method():
			nonlocal output
			nonlocal docker_container_instance
			nonlocal script_arguments
			nonlocal script_file_path
			nonlocal concat_script_arguments

			if len(script_arguments) == 0:
				docker_container_instance.execute_command(
					command=f"python {script_file_path}"
				)
			else:
				docker_container_instance.execute_command(
					command=f"python {script_file_path} {concat_script_arguments}"
				)

			docker_container_instance.wait()

			output = docker_container_instance.get_stdout()

		timeout_thread = TimeoutThread(timeout_thread_method, timeout_seconds)
		timeout_thread.start()

		is_successful = timeout_thread.try_wait()

		docker_container_instance.stop()
		docker_container_instance.remove()
		docker_manager.dispose()

		if not is_successful:
			raise DockerContainerInstanceTimeoutException()

		return output.decode()
