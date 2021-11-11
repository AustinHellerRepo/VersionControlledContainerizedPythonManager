import unittest
from src.austinhellerrepo.version_controlled_containerized_python_manager import VersionControlledContainerizedPythonManager, VersionControlledContainerizedPythonInstance, DockerContainerInstanceTimeoutException
from austin_heller_repo.git_manager import GitManager
import tempfile
import docker


class VersionControlledContainerizedPythonManagerTest(unittest.TestCase):

	def setUp(self) -> None:

		docker_client = docker.from_env()

		image_names = [
			"vccpm_testdockertimedelay"
		]

		for image_name in image_names:

			try:
				docker_client.containers.get(f"{image_name}").kill()
			except Exception as ex:
				pass

			try:
				docker_client.containers.get(f"{image_name}").remove()
			except Exception as ex:
				pass

			try:
				docker_client.images.remove(
					image=f"{image_name}"
				)
			except Exception as ex:
				pass

		docker_client.close()

	def test_initialize(self):

		temp_directory = tempfile.TemporaryDirectory()

		git_manager = GitManager(
			git_directory_path=temp_directory.name
		)

		vccpm = VersionControlledContainerizedPythonManager(
			git_manager=git_manager
		)

		self.assertIsNotNone(vccpm)

		temp_directory.cleanup()

	def test_run_time_delay_script_timeout_failed(self):

		temp_directory = tempfile.TemporaryDirectory()

		git_manager = GitManager(
			git_directory_path=temp_directory.name
		)

		vccpm = VersionControlledContainerizedPythonManager(
			git_manager=git_manager
		)

		with vccpm.run_python_script(
			git_repo_clone_url="https://github.com/AustinHellerRepo/TestDockerTimeDelay.git",
			script_file_path="start.py",
			script_arguments=[],
			timeout_seconds=5
		) as vccpmi:
			with self.assertRaises(DockerContainerInstanceTimeoutException):
				vccpmi.wait()

		temp_directory.cleanup()

	def test_run_time_delay_script(self):

		temp_directory = tempfile.TemporaryDirectory()

		git_manager = GitManager(
			git_directory_path=temp_directory.name
		)

		vccpm = VersionControlledContainerizedPythonManager(
			git_manager=git_manager
		)

		with vccpm.run_python_script(
			git_repo_clone_url="https://github.com/AustinHellerRepo/TestDockerTimeDelay.git",
			script_file_path="start.py",
			script_arguments=[],
			timeout_seconds=20
		) as vccpmi:
			vccpmi.wait()
			output = vccpmi.get_output()

		self.assertEqual('{ "data": [ ], "exception": null }\n', output)

		temp_directory.cleanup()
